# WireGuard is new, fast and recommanded vpn than L2TP.

# This script is unstable and not maintained any more. Please find a better one.

# l2tp-client
script for l2tp (only pskshared secret) client tested on debian 8


## install packages:
```sh
sudo apt-get install strongswan xl2tpd python3
```

## user and password are kept in config.ini 



## How to make a l2tp-vpn connection:
```sh
sudo python3 connect.py
```



### manual source:
http://www.jasonernst.com/2016/06/21/l2tp-ipsec-vpn-on-ubuntu-16-04/
