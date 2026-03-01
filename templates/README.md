# Templates – Cấu hình apply qua terminal (Jinja)

Cấu trúc: **vendor** → **series** → **từng loại config** (file `.j2`).

User điền biến vào, render Jinja ra **text config**, apply xuống device qua **terminal** (SSH/CLI), không dùng NETCONF.

## Cấu trúc thư mục

```
templates/
├── juniper/
│   ├── mx/          # add_vlan, config_isis, config_bgp_ls, config_ospf, config_bgp, config_interface, config_snmp, config_ntp, config_syslog
│   ├── ex/
│   └── srx/
├── cisco/
│   ├── catalyst/    # add_vlan, config_isis, config_bgp_ls, config_ospf, config_bgp, config_interface, config_snmp, config_ntp, config_syslog, config_acl
│   └── ios-xe/
├── samsung/
│   └── exalink/
├── hdn/
│   └── switch/
└── ubiquoss/
    └── olt/         # add_ont, add_vlan, config_snmp, config_management, config_interface, config_ntp, config_syslog
```

## Loại config (theo series)

- **add_vlan** – Thêm VLAN
- **config_isis** – Cấu hình IS-IS
- **config_bgp_ls** – Cấu hình BGP-LS
- **config_bgp** – Cấu hình BGP
- **config_ospf** – Cấu hình OSPF
- **config_interface** – Cấu hình interface
- **config_snmp** – Cấu hình SNMP
- **config_ntp** – Cấu hình NTP
- **config_syslog** – Cấu hình syslog
- **config_acl** – Cấu hình ACL (Cisco)
- **add_ont** – Đăng ký ONU (Ubiquoss OLT)
- **config_management** – Cấu hình management (Ubiquoss OLT)

Biến cho từng template xem trong comment đầu file `.j2`.
