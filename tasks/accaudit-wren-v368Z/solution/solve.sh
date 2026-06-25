#!/bin/bash
set -euo pipefail

cat << 'WREN_EOF' > /app/audit.wren
import "io" for File

// String byte value at index i
var byteAt = Fn.new { |s, i| s[i].bytes[0] }

// Lexicographic string comparison: returns -1, 0, or 1
var strCmp = Fn.new { |a, b|
  var len = a.count < b.count ? a.count : b.count
  for (i in 0...len) {
    var ca = byteAt.call(a, i)
    var cb = byteAt.call(b, i)
    if (ca < cb) return -1
    if (ca > cb) return  1
  }
  if (a.count < b.count) return -1
  if (a.count > b.count) return  1
  return 0
}

var strGt = Fn.new { |a, b| strCmp.call(a, b) > 0 }

var isDigit = Fn.new { |c|
  var b = byteAt.call(c, 0)
  return b >= 48 && b <= 57
}

var allDigits = Fn.new { |s|
  if (s.count == 0) return false
  for (i in 0...s.count) {
    if (!isDigit.call(s[i])) return false
  }
  return true
}

var parseUint = Fn.new { |s|
  var n = 0
  for (i in 0...s.count) {
    n = n * 10 + (byteAt.call(s, i) - 48)
  }
  return n
}

// Valid non-negative decimal: one or more digits, optional single dot
var isDecimal = Fn.new { |s|
  if (s.count == 0) return false
  var hasDot = false
  var hasDigit = false
  for (i in 0...s.count) {
    var c = s[i]
    if (c == ".") {
      if (hasDot) return false
      hasDot = true
    } else if (isDigit.call(c)) {
      hasDigit = true
    } else {
      return false
    }
  }
  return hasDigit
}

// Integer cents from a valid decimal string (exact; no floating point)
var parseCents = Fn.new { |s|
  var dot = -1
  for (i in 0...s.count) {
    if (s[i] == ".") {
      dot = i
      break
    }
  }
  var whole = ""
  var frac = ""
  if (dot == -1) {
    whole = s
  } else {
    whole = s[0...dot]
    frac = s[(dot + 1)...s.count]
  }
  if (whole.count == 0) whole = "0"
  if (frac.count == 0) frac = "00"
  if (frac.count == 1) frac = frac + "0"
  if (frac.count > 2) frac = frac[0..1]
  return parseUint.call(whole) * 100 + parseUint.call(frac)
}

var daysInMonth = Fn.new { |y, m|
  if (m == 2) return ((y % 4 == 0 && y % 100 != 0) || y % 400 == 0) ? 29 : 28
  if ([4, 6, 9, 11].contains(m)) return 30
  return 31
}

// True if s is valid YYYYMMDD with date <= 2026-06-13
var isValidDate = Fn.new { |s|
  if (s.count != 8) return false
  if (!allDigits.call(s)) return false
  if (strGt.call(s, "20260613")) return false
  var y = parseUint.call(s[0..3])
  var m = parseUint.call(s[4..5])
  var d = parseUint.call(s[6..7])
  if (m < 1 || m > 12) return false
  if (d < 1 || d > daysInMonth.call(y, m)) return false
  return true
}

var VALID_TYPES      = ["CREDIT", "DEBIT", "FEE", "INTEREST", "REVERSAL"]
var VALID_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF"]

var jsonEsc = Fn.new { |s|
  return s.replace("\\", "\\\\").replace("\"", "\\\"")
}

// Insertion sort error records by (account_id, error_code, txn_id) ascending
var sortErrors = Fn.new { |arr|
  if (arr.count < 2) return
  for (i in 1...arr.count) {
    var key = arr[i]
    var j = i - 1
    while (j >= 0) {
      var a = arr[j]
      var c = strCmp.call(a["account_id"], key["account_id"])
      if (c == 0) c = strCmp.call(a["error_code"], key["error_code"])
      if (c == 0) c = strCmp.call(a["txn_id"], key["txn_id"])
      if (c <= 0) break
      arr[j + 1] = arr[j]
      j = j - 1
    }
    arr[j + 1] = key
  }
}

// Insertion sort transactions by (date, txn_id) ascending
var sortTxns = Fn.new { |arr|
  if (arr.count < 2) return
  for (i in 1...arr.count) {
    var key = arr[i]
    var j = i - 1
    while (j >= 0) {
      var a = arr[j]
      var c = strCmp.call(a["date"], key["date"])
      if (c == 0) c = strCmp.call(a["txn_id"], key["txn_id"])
      if (c <= 0) break
      arr[j + 1] = arr[j]
      j = j - 1
    }
    arr[j + 1] = key
  }
}

// ── main ─────────────────────────────────────────────────────────────────────

var content  = File.read("/app/transactions.tsv")
var lines    = content.split("\n")
var errors   = []
var txnSeen  = {}
var acctIds  = []          // preserve first-seen account order (deterministic)
var acctTxns = {}

for (rawLine in lines) {
  var line = rawLine.trim()
  if (line.count == 0) continue

  var fields = line.split("\t")
  var txnId  = fields.count > 0 ? fields[0] : "?"
  var acctId = fields.count > 1 ? fields[1] : "?"

  if (fields.count < 6) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "MISSING_FIELD",
                "detail": "expected 6 fields, got %(fields.count)"})
    continue
  }

  var date      = fields[2]
  var amountStr = fields[3]
  var typeName  = fields[4]
  var currency  = fields[5]

  var txnIdOk = txnId.count == 10 && txnId[0] == "T" && allDigits.call(txnId[1..9])
  if (!txnIdOk) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "BAD_TXN_ID",
                "detail": "must be T followed by 9 digits"})
  }

  var acctIdOk = acctId.count == 8 && acctId[0..1] == "AC" && allDigits.call(acctId[2..7])
  if (!acctIdOk) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "BAD_ACCT_ID",
                "detail": "must be AC followed by 6 digits"})
  }

  var dateOk = isValidDate.call(date)
  if (!dateOk) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "BAD_DATE",
                "detail": "invalid or future date"})
  }

  var amountOk = isDecimal.call(amountStr)
  if (!amountOk) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "BAD_AMOUNT",
                "detail": "must be a non-negative decimal"})
  }

  var typeOk = VALID_TYPES.contains(typeName)
  if (!typeOk) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "BAD_TYPE",
                "detail": "must be CREDIT, DEBIT, FEE, INTEREST, or REVERSAL"})
  }

  var currOk = VALID_CURRENCIES.contains(currency)
  if (!currOk) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "BAD_CURRENCY",
                "detail": "must be USD, EUR, GBP, JPY, or CHF"})
  }

  var isDup = txnSeen.containsKey(txnId)
  if (isDup) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "DUPLICATE_TXN",
                "detail": "transaction ID seen more than once"})
  } else {
    txnSeen[txnId] = true
  }

  if (typeOk && typeName == "FEE" && amountOk && parseCents.call(amountStr) > 2500) {
    errors.add({"txn_id": txnId, "account_id": acctId,
                "error_code": "FEE_OVERCAP",
                "detail": "fee amount %(amountStr) exceeds the 25.00 cap"})
  }

  if (!isDup && txnIdOk && acctIdOk && dateOk && amountOk && typeOk && currOk) {
    if (!acctTxns.containsKey(acctId)) {
      acctTxns[acctId] = []
      acctIds.add(acctId)
    }
    acctTxns[acctId].add({"txn_id": txnId, "date": date,
                          "cents": parseCents.call(amountStr), "type": typeName})
  }
}

for (acctId in acctIds) {
  var txns = acctTxns[acctId]
  sortTxns.call(txns)

  // velocity: >5 DEBIT on the same date → HIGH_VELOCITY and frozen (held)
  var debitDates = {}
  for (t in txns) {
    if (t["type"] == "DEBIT") {
      var d = t["date"]
      if (!debitDates.containsKey(d)) debitDates[d] = []
      debitDates[d].add(t["txn_id"])
    }
  }
  var frozen = {}
  for (d in debitDates.keys) {
    var ids = debitDates[d]
    if (ids.count > 5) {
      for (tid in ids) {
        errors.add({"txn_id": tid, "account_id": acctId,
                    "error_code": "HIGH_VELOCITY",
                    "detail": "more than 5 debit transactions on %(d)"})
        frozen[tid] = true
      }
    }
  }

  var balance     = 0
  var openCharges = []   // {txn_id, cents, reversed}
  for (t in txns) {
    var typ = t["type"]
    if (typ == "CREDIT" || typ == "INTEREST") {
      balance = balance + t["cents"]
    } else if (typ == "REVERSAL") {
      var matchIdx = -1
      var k = openCharges.count - 1
      while (k >= 0) {
        var oc = openCharges[k]
        if (!oc["reversed"] && oc["cents"] == t["cents"]) {
          matchIdx = k
          break
        }
        k = k - 1
      }
      if (matchIdx >= 0) {
        openCharges[matchIdx]["reversed"] = true
        balance = balance + t["cents"]
      } else {
        errors.add({"txn_id": t["txn_id"], "account_id": acctId,
                    "error_code": "UNMATCHED_REVERSAL",
                    "detail": "reversal has no matching prior charge"})
      }
    } else {  // DEBIT or FEE
      if (frozen.containsKey(t["txn_id"])) {
        // held velocity debit: does not post, not reversible
      } else {
        balance = balance - t["cents"]
        openCharges.add({"txn_id": t["txn_id"], "cents": t["cents"], "reversed": false})
        if (balance < 0) {
          errors.add({"txn_id": t["txn_id"], "account_id": acctId,
                      "error_code": "OVERDRAFT",
                      "detail": "running balance fell below zero"})
        }
      }
    }
  }
}

sortErrors.call(errors)

var out = "[\n"
for (i in 0...errors.count) {
  var e = errors[i]
  out = out +
    "  {\"txn_id\": \"" + jsonEsc.call(e["txn_id"]) + "\", " +
    "\"account_id\": \"" + jsonEsc.call(e["account_id"]) + "\", " +
    "\"error_code\": \"" + jsonEsc.call(e["error_code"]) + "\", " +
    "\"detail\": \"" + jsonEsc.call(e["detail"]) + "\"}"
  if (i < errors.count - 1) out = out + ","
  out = out + "\n"
}
out = out + "]"

System.print(out)
WREN_EOF

wren_cli /app/audit.wren > /app/audit_report.json
