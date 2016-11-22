"""Your awesome Distance Vector router for CS 168."""

import sim.api as api
import sim.basics as basics
from itertools import product

# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter(basics.DVRouterBase):
    # NO_LOG = True # Set to True on an instance to disable its logging
    # POISON_MODE = True # Can override POISON_MODE here
    # DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

    def __init__(self):
        """
        Called when the instance is initialized.

        You probably want to do some additional initialization here.

        """
        self.start_timer()      # Starts calling handle_timer() at correct rate
        self.my_HOST = {}
        self.route_TABLE = {}   # { host : (cost, port, time) }
        self.D_VECTORS = {}     # {neigh : {dest:latency}}
        self.links = {}
        self.neighbours = {}

        # self.route_TABLE[self] = {self: (0)}

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed
        in.

        """
        self.links[port] = latency
        # sending routing table
        for x in self.route_TABLE.keys():
            cost = self.route_TABLE[x][0]
            self.send(basics.RoutePacket(x, cost), port, flood=False)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.

        """
        del self.links[port]
        del self.neighbours[port]
        for host in self.route_TABLE.keys():
            if self.route_TABLE[host][1] == port:
                pass

    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        # self.log("RX %s on %s (%s)", packet, port, api.current_time())
        if isinstance(packet, basics.RoutePacket):
            self.handle_RoutePacket(packet, port)
        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.handle_HostDiscoveryPacket(packet, port)
        else:
            self.handle_DataPacket(packet, port)

    def handle_RoutePacket(self, packet, port):
        """
        Called by handle_rx to Route packets

        """
        time = api.current_time()
        if packet.src not in self.neighbours.keys():
            self.neighbours[packet.src] = port

        if packet.src not in self.D_VECTORS.keys():
            self.D_VECTORS[packet.src] = {}

        self.D_VECTORS[packet.src].update({packet.destination: packet.latency})

        if packet.destination not in self.route_TABLE.keys():
            self.route_TABLE[packet.destination] = (INFINITY, port, time)

        for x in self.D_VECTORS.keys():
            cost = self.links[port] + self.D_VECTORS[packet.src][packet.destination]
            if cost < self.route_TABLE[packet.destination][0]:
                self.route_TABLE[packet.destination] = (cost, port, time)

    def handle_HostDiscoveryPacket(self, packet, port):
        """
        Called by handle_rx to Host discovery pacts packets

        """
        if packet.src is not None and packet.src not in self.my_HOST.keys():
            self.my_HOST[packet.src] = port

    def handle_DataPacket(self, packet, port):
        """
        Called by handle_rx to other packets

        """
        if packet.dst in self.my_HOST.keys():
            self.send(packet, self.my_HOST[packet.dst], flood=False)
        elif packet.dst in self.route_TABLE.keys():
            out_port = self.route_TABLE[packet.dst][1]
            self.send(packet, out_port, flood=False)
        else:
            self.send(packet, port, flood=True)

    def handle_timer(self):
        """
        Called periodically.

        When called, your router should send tables to neighbors.  It
        also might not be a bad place to check for whether any entries
        have expired.

        """
        for x in self.route_TABLE.keys():
            cost, port, time = self.route_TABLE[x]
            if api.current_time() - time >= 15:
                self.route_TABLE[x] = (INFINITY, port, time)

        for x, y in product(self.neighbours.keys(), self.route_TABLE.keys()):
            port = self.neighbours[x]
            cost = self.route_TABLE[y][0]
            self.send(basics.RoutePacket(x, cost), port, flood=False)
