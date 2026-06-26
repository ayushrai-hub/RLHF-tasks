package vaultshard

/** CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no final xor). */
object Crc {
  def crc16CcittFalse(data: Array[Byte]): Int = {
    var crc = 0xFFFF
    var idx = 0
    while (idx < data.length) {
      crc ^= (data(idx) & 0xFF) << 8
      var bit = 0
      while (bit < 8) {
        if ((crc & 0x8000) != 0) crc = ((crc << 1) ^ 0x1021) & 0xFFFF
        else crc = (crc << 1) & 0xFFFF
        bit += 1
      }
      idx += 1
    }
    crc & 0xFFFF
  }

  def hex4(value: Int): String = "%04x".format(value & 0xFFFF)
}
