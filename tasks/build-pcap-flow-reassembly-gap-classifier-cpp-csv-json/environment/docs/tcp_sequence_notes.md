# TCP Sequence Notes

Payload bytes advance sequence space. SYN and FIN flags also each consume one sequence number, even when payload length is zero.

ACK-only rows consume no sequence space. They should still appear as segment rows because they are part of the exported metadata timeline.
