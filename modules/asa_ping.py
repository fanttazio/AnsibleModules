#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: asa_ping
short_description: Tests reachability using ping from Cisco ASA network devices
description:
- Tests reachability using ping from firewall to a remote destination.
- For a general purpose network module, see the M(net_ping) module.
- For Windows targets, use the M(win_ping) module instead.
- For targets running Python, use the M(ping) module instead.
author:
- Mehdi Rashidi. Adopted from ios_ping module by Jacob McGill (@jmcgill298)
version_added: '2.9.2'
extends_documentation_fragment: asa
options:
  count:
    description:
    - Number of packets to send.
    default: 5
  dest:
    description:
    - The IP Address or hostname (resolvable by firewall) of the remote node.
    required: true
  source:
    description:
    - The source IP Address.
  state:
    description:
    - Determines if the expected result is success or fail.
    choices: [ absent, present ]
    default: present
notes:
  - For a general purpose network module, see the M(net_ping) module.
  - For Windows targets, use the M(win_ping) module instead.
  - For targets running Python, use the M(ping) module instead.
'''

EXAMPLES = r'''



- name: Test reachability to 10.20.20.20 
  asa_ping:
    dest: 10.20.20.20

- name: Test unreachability to 10.30.30.30 
  asa_ping:
    dest: 10.30.30.30
    state: absent

- name: Test reachability to 10.40.40.40 and setting count and source
  asa_ping:
    dest: 10.40.40.40
    source: loopback0
    count: 20
'''

RETURN = '''
commands:
  description: Show the command sent.
  returned: always
  type: list
  sample: ["ping 10.40.40.40 count 20 source loopback0"]
packet_loss:
  description: Percentage of packets lost.
  returned: always
  type: str
  sample: "0%"
packets_rx:
  description: Packets successfully received.
  returned: always
  type: int
  sample: 20
packets_tx:
  description: Packets successfully transmitted.
  returned: always
  type: int
  sample: 20
rtt:
  description: Show RTT stats.
  returned: always
  type: dict
  sample: {"avg": 2, "max": 8, "min": 1}
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.asa.asa import run_commands
from ansible.module_utils.network.asa.asa import asa_argument_spec
import re


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        count=dict(type="int"),
        dest=dict(type="str", required=True),
        source=dict(type="str"),
        state=dict(type="str", choices=["absent", "present"], default="present")
    )

    argument_spec.update(asa_argument_spec)

    module = AnsibleModule(argument_spec=argument_spec)

    count = module.params["count"]
    dest = module.params["dest"]
    source = module.params["source"]

    warnings = list()

    results = {}
    if warnings:
        results["warnings"] = warnings

    results["commands"] = [build_ping(dest, count, source)]

    ping_results = run_commands(module, commands=results["commands"])
    ping_results_list = ping_results[0].split("\n")

    stats = ""
    for line in ping_results_list:
        if line.startswith('Success'):
            stats = line

    success, rx, tx, rtt = parse_ping(stats)
    loss = abs(100 - int(success))
    results["packet_loss"] = str(loss) + "%"
    results["packets_rx"] = int(rx)
    results["packets_tx"] = int(tx)

    # Convert rtt values to int
    for k, v in rtt.items():
        if rtt[k] is not None:
            rtt[k] = int(v)

    results["rtt"] = rtt

    validate_results(module, loss, results)

    module.exit_json(**results)


def build_ping(dest, count=None, source=None):
    """
    Function to build the command to send to the terminal for the switch
    to execute. All args come from the module's unique params.
    """
    cmd = "ping {0}".format(dest)

    if count is not None:
        cmd += " repeat {0}".format(str(count))

    if source is not None:
        cmd += " source {0}".format(source)

    return cmd


def parse_ping(ping_stats):
    """
    Function used to parse the statistical information from the ping response.
    Example: "Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/8 ms"
    Returns the percent of packet loss, received packets, transmitted packets, and RTT dict.
    """
    rate_re = re.compile(r"^\w+\s+\w+\s+\w+\s+(?P<pct>\d+)\s+\w+\s+\((?P<rx>\d+)/(?P<tx>\d+)\)")
    rtt_re = re.compile(r".*,\s+\S+\s+\S+\s+=\s+(?P<min>\d+)/(?P<avg>\d+)/(?P<max>\d+)\s+\w+\s*$|.*\s*$")

    rate = rate_re.match(ping_stats)
    rtt = rtt_re.match(ping_stats)

    return rate.group("pct"), rate.group("rx"), rate.group("tx"), rtt.groupdict()


def validate_results(module, loss, results):
    """
    This function is used to validate whether the ping results were unexpected per "state" param.
    """
    state = module.params["state"]
    if state == "present" and loss == 100:
        module.fail_json(msg="Ping failed unexpectedly", **results)
    elif state == "absent" and loss < 100:
        module.fail_json(msg="Ping succeeded unexpectedly", **results)


if __name__ == "__main__":
    main()
