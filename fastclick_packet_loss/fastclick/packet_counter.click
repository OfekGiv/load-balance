ControlSocket(TCP, 1234);


define(
  $DEV         0,               // DPDK port id, or use FromDevice for kernel
  $SRC         10.0.0.1,        // source IPv4
  $DST         192.168.0.1,     // destination IPv4
  $PROMISC     true,            // set false if you like
);

in :: FromDPDKDevice($DEV, PROMISC $PROMISC);

in -> Strip(14) -> CheckIPHeader -> ip  :: IPClassifier(src host $SRC && dst host $DST, -);

ip[0] -> c_match :: Counter -> Discard;
ip[1] -> Discard;

