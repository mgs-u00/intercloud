from mn.net import Mininet
from mn.node import RemoteController
from mn.cli import CLI
from mn.log import setLogLevel, info

def topology():
    net = Mininet(controller=RemoteController)

    info("Adding controller:\n")
    net.addController('c0', controller=RemoteController, ip="127.0.0.1", port=6633)

    info("Adding hosts:\n")
    
    # Sources
    h1 = net.addHost('h1')
    
    info("Adding servers:\n")
    # Destinations
    d1 = net.addHost('d1')
    

    # info(f"Host 2: {str(h2.checkSetup)}")

    info("Adding switches: \n")
    s1 = net.addSwitch('s1')

    info("Making links:\n")
    net.addLink(s1, h1)
    net.addLink(s1, d1)

    info("Network Start:\n")
    net.start()

    info("CLI:\n")
    CLI(net)

    info("Stopping network...")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()
