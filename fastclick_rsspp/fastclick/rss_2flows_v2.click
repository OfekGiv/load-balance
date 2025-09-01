
ControlSocket("TCP",1234);

// Two RX queues from the same port
fd0 :: FromDPDKDevice(0, QUEUE 0, N_QUEUES 1, PROMISC true);
fd1 :: FromDPDKDevice(0, QUEUE 1, N_QUEUES 1, PROMISC true);

fd0 -> Discard;
fd1 -> Discard;

StaticThreadSched(fd0 0, fd1 1);


