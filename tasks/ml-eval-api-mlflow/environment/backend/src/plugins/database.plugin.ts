import fp from 'fastify-plugin';
import { FastifyInstance } from 'fastify';
import { Kysely, PostgresDialect, sql } from 'kysely';
import { Database } from '../modules/users/users.model';
import pg from 'pg';

async function databasePlugin(fastify: FastifyInstance) {
  const { config } = fastify;

  if (!config.DB_ENABLED) {
    const throwDisabled = () => {
      throw new Error(
        'Database is disabled. Set DB_ENABLED=true to enable database access.'
      );
    };

    const disabledDatabase = {
      selectFrom: throwDisabled,
      insertInto: throwDisabled,
      updateTable: throwDisabled,
      deleteFrom: throwDisabled,
      executeQuery: throwDisabled,
      transaction: throwDisabled,
      destroy: async () => undefined
    } as unknown as Kysely<Database>;

    fastify.decorate('database', disabledDatabase);
    fastify.log.warn('Database connection is disabled via DB_ENABLED');
    return;
  }

  const dialect = new PostgresDialect({
    pool: new pg.Pool({
      host: config.DB_TEST_HOST || config.DB_HOST,
      port: config.DB_TEST_PORT || config.DB_PORT,
      user: config.DB_TEST_USER || config.DB_USER,
      password: config.DB_TEST_PASSWORD || config.DB_PASSWORD,
      database: config.DB_TEST_NAME || config.DB_NAME,
      max: config.DB_TEST_POOL_MAX || config.DB_POOL_MAX,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000
    })
  });

  const db = new Kysely<Database>({ dialect });

  try {
    await sql`SELECT 1`.execute(db);
    fastify.log.debug('Database connection health check passed');

    fastify.decorate('database', db);

    fastify.addHook('onClose', async () => {
      await db.destroy();
      fastify.log.info('Kysely Database connection pool closed');
    });
  } catch (error) {
    fastify.log.error('Database connection failed during startup');
    throw error;
  }
}

export default fp(databasePlugin, {
  name: 'database',
  dependencies: ['config']
});
