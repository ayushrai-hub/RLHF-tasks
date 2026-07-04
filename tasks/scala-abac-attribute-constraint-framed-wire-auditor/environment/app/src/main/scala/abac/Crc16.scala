package abac

object Crc16:
  def crc16Ccitt(data: Array[Byte]): Int = ccitt(data)

  def ccitt(data: Array[Byte]): Int =
    var crc = 0xFFFF
    var i = 0
    while i < data.length do
      crc = crc ^ ((data(i) & 0xFF) << 8)
      var bit = 0
      while bit < 8 do
        crc =
          if (crc & 0x8000) != 0 then ((crc << 1) ^ 0x1021) & 0xFFFF
          else (crc << 1) & 0xFFFF
        bit += 1
      i += 1
    crc
