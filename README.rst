requests-safe
-------------

This project provides an ``HTTPAdapter`` for the Requests_ library that will
disallow connections to networks that are considered unsafe to connect to.

The primary use case is to safely be able to retrieve items from a user
provided URL without potentially requesting internal or secret resources within
ones own network.

IPv4 unsafe networks
~~~~~~~~~~~~~~~~~~~~

These are the IPv4 networks that are blocked from being conneted to:

=========================      ==================
         Name                  Network (CIDR)
-------------------------      ------------------
RFC1918 (private network)      10.0.0.0/8
                               172.16.0.0/12
                               192.168.0.0/16
Link-Local                     169.254.0.0/16
CG-NAT address space           100.64.0.0/10
Localhost/loopback             127.0.0.0/8
Any IP in Linux                0.0.0.0/32
IETF Protocol Assignments      192.0.0.0/24
TEST-NET-1                     192.0.2.0/24
RESERVED                       192.88.99.0/24
Benchmark testing              198.18.0.0/15
TEST-NET-2                     198.51.100.0/24
TEST-NET-3                     203.0.113.0/24
IP Multicast                   224.0.0.0/4
RESERVED                       240.0.0.0/4
Limited broadcast              255.255.255.255/32
=========================      ==================

IPv6 unsafe networks
~~~~~~~~~~~~~~~~~~~~

These are the IPv6 networks that are blocked from being connected to:

=============================        ==================
         Name                        Network (CIDR)
-----------------------------        ------------------
Localhost/unspecified address        ::/128
Loopback                             ::1/128
IPv4 mapped address                  ::ffff:0:0/96
IPv4 translated addresses            ::ffff:0:0:0/96
IPv4/IPv6 translation                64:ff9b::/96
Discard prefix                       100::/64
Teredo tunneling                     2001::/32
Orchid v2 (abondoned)                2001:20::/28
Documentation                        2001:db8::/32
6to4 addressing scheme               2002::/16
ULA address space                    fc00::/7
Link-local address space             fe80::/10
Global multicast                     ff00::/8
=============================        ==================

.. _Requests: http://docs.python-requests.org/en/master/
