from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def topology():
    net = Mininet(controller=RemoteController)

    info("Adding controller:\n")
    net.addController('c0', controller=RemoteController, ip="127.0.0.1", port=6633)

    info("Adding hosts:\n")
    
    # Sources
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')
    h5 = net.addHost('h5')
    h6 = net.addHost('h6')
    
    
    # Destinations
    d1 = net.addHost('d1')
    d1 = net.addHost('d2')
    d1 = net.addHost('d3')
    

    # info(f"Host 2: {str(h2.checkSetup)}")

    info("Adding switches: \n")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')
    s5 = net.addSwitch('s5')
    s6 = net.addSwitch('s6')
    s7 = net.addSwitch('s7')

    info("Making links:\n")
    net.addLink(s1, s2)
    net.addLink(s1, s3)
    net.addLink(s2, s5)
    net.addLink(s2, s4)
    net.addLink(s3, s6)
    net.addLink(s3, s7)
    net.addLink(s4, h1)
    net.addLink(s4, h2)
    net.addLink(s5, h3)
    net.addLink(s6, h4)
    net.addLink(s7, h6)
    net.addLink(s7, h5)

    info("Network Start:\n")
    net.start()

    info("CLI:\n")
    CLI(net)

    info("Stopping network...")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()
