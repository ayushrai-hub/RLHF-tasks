#!/bin/bash
# Oracle solution: enforce inactive-user blocking in the Express/Prisma API.
#
# Four files are modified:
#   1. src/features/auth/repositories/auth.repository.ts
#      – add `active` to the findByEmail select
#      – add a new findUserById method
#   2. src/features/auth/services/auth.service.ts
#      – reject login when user.active is false
#      – reject refresh when the account owner is inactive
#      – restore the duplicate-email check in register
#   3. src/middleware/authenticate.middleware.ts
#      – after JWT verification, look up the user's active flag in the DB
#        and return 401 when the account is inactive
#   4. src/features/user/repositories/user.repository.ts
#      – filter findAll to only return active users

set -e
cd /app

# ── 1. auth.repository.ts ─────────────────────────────────────────────────
cat > src/features/auth/repositories/auth.repository.ts << 'REPOEOF'
import type { PrismaClient } from "../../../../generated/prisma/client.js";
import { DEFAULT_ROLE_NAME } from "../../../constants/roles.js";

export class AuthRepository {
    constructor(private readonly prisma: PrismaClient) {}

    async findByEmail(email: string) {
        return this.prisma.user.findUnique({
            where: { email },
            select: {
                id: true,
                email: true,
                password: true,
                firstname: true,
                lastname: true,
                active: true,
                role: { select: { name: true } },
            },
        });
    }

    async findUserById(id: number) {
        return this.prisma.user.findUnique({
            where: { id },
            select: { id: true, active: true },
        });
    }

    async createUser(data: {
        email: string;
        password: string;
        firstname?: string;
        lastname?: string;
    }) {
        return this.prisma.user.create({
            data: {
                email: data.email,
                password: data.password,
                firstname: data.firstname,
                lastname: data.lastname,
                role: {
                    connect: {
                        name: DEFAULT_ROLE_NAME,
                    },
                },
            },
            select: {
                id: true,
                email: true,
                firstname: true,
                lastname: true,
                role: { select: { name: true } },
                createdAt: true,
            },
        });
    }

    async createRefreshToken(data: { userId: number; tokenHash: string; expiresAt: Date }) {
        return this.prisma.refreshToken.create({
            data: {
                userId: data.userId,
                tokenHash: data.tokenHash,
                expiresAt: data.expiresAt,
            },
        });
    }

    async findRefreshToken(tokenHash: string) {
        return this.prisma.refreshToken.findUnique({
            where: { tokenHash },
        });
    }

    async revokeRefreshToken(tokenHash: string) {
        return this.prisma.refreshToken.update({
            where: { tokenHash },
            data: { revokedAt: new Date() },
        });
    }
}
REPOEOF

# ── 2. auth.service.ts ────────────────────────────────────────────────────
cat > src/features/auth/services/auth.service.ts << 'SVCEOF'
import bcrypt from "bcryptjs";
import crypto from "crypto";

import type { RoleName } from "../../../../generated/prisma/client.js";
import { env } from "../../../config/env-config.js";
import { signRefreshToken, signToken, verifyRefreshToken } from "../../../utils/jwt.util.js";
import { parseDurationMs } from "../../../utils/time.util.js";
import type { AuthRepository } from "../repositories/auth.repository.js";
import type { LoginInput, RegisterInput } from "../schemas/auth.schema.js";

export class AuthService {
    constructor(private readonly repo: AuthRepository) {}

    private async buildRefreshToken(userId: number, role: RoleName): Promise<string> {
        const rawToken = signRefreshToken({ userId, role });
        const tokenHash = crypto.createHash("sha256").update(rawToken).digest("hex");
        const expiresAt = new Date(Date.now() + parseDurationMs(env.REFRESH_TOKEN_EXPIRES_IN));
        await this.repo.createRefreshToken({ userId, tokenHash, expiresAt });
        return rawToken;
    }

    async register(input: RegisterInput) {
        const email = input.email.trim().toLowerCase();

        const existing = await this.repo.findByEmail(email);
        if (existing) {
            return {
                success: false,
                message: "User already exists with this email",
            };
        }

        const hashedPassword = await bcrypt.hash(input.password, 12);

        const user = await this.repo.createUser({
            email,
            password: hashedPassword,
            firstname: input.firstname?.trim(),
            lastname: input.lastname?.trim(),
        });

        const accessToken = signToken({
            userId: user.id,
            role: user.role.name,
        });
        const refreshToken = await this.buildRefreshToken(user.id, user.role.name);

        return {
            success: true,
            message: "Registration successful",
            data: { ...user, accessToken },
            refreshToken,
        };
    }

    async login(input: LoginInput) {
        const email = input.email.trim().toLowerCase();

        const user = await this.repo.findByEmail(email);
        if (!user) {
            return { success: false, message: "Invalid credentials" };
        }

        const passwordMatch = await bcrypt.compare(input.password, user.password);
        if (!passwordMatch) {
            // To prevent user enumeration, return the same message for both cases
            return { success: false, message: "Invalid credentials" };
        }

        if (!user.active) {
            return { success: false, message: "Account is inactive" };
        }

        // Exclude password from the returned user data
        const { password: _, active: __, ...safeUser } = user;
        const accessToken = signToken({
            userId: user.id,
            role: user.role.name,
        });
        const refreshToken = await this.buildRefreshToken(user.id, user.role.name);

        return {
            success: true,
            message: "Login successful",
            data: { ...safeUser, accessToken },
            refreshToken,
        };
    }

    async refresh(rawToken: string) {
        const tokenHash = crypto.createHash("sha256").update(rawToken).digest("hex");
        const stored = await this.repo.findRefreshToken(tokenHash);

        if (!stored || stored.revokedAt || stored.expiresAt < new Date()) {
            return {
                success: false,
                message: "Invalid or expired refresh token",
            };
        }

        // Reject refresh for inactive accounts
        const user = await this.repo.findUserById(stored.userId);
        if (!user || !user.active) {
            return { success: false, message: "Account is inactive" };
        }

        // Verify JWT signature
        const payload = verifyRefreshToken(rawToken);

        // Rotate: revoke old token, issue new one
        await this.repo.revokeRefreshToken(tokenHash);
        const newAccessToken = signToken({
            userId: payload.userId,
            role: payload.role,
        });
        const newRefreshToken = await this.buildRefreshToken(payload.userId, payload.role);

        return {
            success: true,
            data: { accessToken: newAccessToken },
            refreshToken: newRefreshToken,
        };
    }

    async logout(rawToken: string) {
        const tokenHash = crypto.createHash("sha256").update(rawToken).digest("hex");
        await this.repo.revokeRefreshToken(tokenHash);
        return { success: true, message: "Logged out successfully" };
    }
}
SVCEOF

# ── 3. authenticate.middleware.ts ─────────────────────────────────────────
cat > src/middleware/authenticate.middleware.ts << 'MIDEOF'
import type { NextFunction, Request, Response } from "express";

import { prisma } from "../config/prisma.js";
import { verifyToken } from "../utils/jwt.util.js";

export const authenticateMiddleware = async (
    req: Request,
    res: Response,
    next: NextFunction,
): Promise<void> => {
    const authHeader = req.headers.authorization;

    if (!authHeader?.startsWith("Bearer ")) {
        res.status(401).json({ success: false, message: "No token provided" });
        return;
    }

    const token = authHeader.split(" ")[1];

    try {
        const payload = verifyToken(token);

        // Reject requests from accounts that have been deactivated after token issuance
        const user = await prisma.user.findUnique({
            where: { id: payload.userId },
            select: { active: true },
        });

        if (!user || !user.active) {
            res.status(401).json({ success: false, message: "Account is inactive" });
            return;
        }

        req.user = payload;
        next();
    } catch {
        res.status(401).json({
            success: false,
            message: "Invalid or expired token",
        });
    }
};
MIDEOF

# ── 4. user.repository.ts ─────────────────────────────────────────────────
cat > src/features/user/repositories/user.repository.ts << 'USEREPO'
import type { PrismaClient } from "../../../../generated/prisma/client.js";

export class UserRepository {
    constructor(private readonly prisma: PrismaClient) {}

    async findAll() {
        return this.prisma.user.findMany({
            where: { active: true },
            include: {
                role: {
                    select: { name: true },
                },
            },
        });
    }
}
USEREPO

# ── 5. Rebuild ────────────────────────────────────────────────────────────
npm run build

