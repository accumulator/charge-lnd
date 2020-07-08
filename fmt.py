from termcolor import colored

def lnd_to_cl_scid(s):
    block = s >> 40
    tx = s >> 16 & 0xFFFFFF
    output = s  & 0xFFFF
    return (block, tx, output)

def cl_to_lnd_scid(s):
    s = [int(i) for i in s.split(':')]
    return (s[0] << 40) | (s[1] << 16) | s[2]

def x_to_lnd_scid(s):
    s = [int(i) for i in s.split('x')]
    return (s[0] << 40) | (s[1] << 16) | s[2]

def parse_channel_id(s):
    if s == None:
        return None
    if ':' in s:
        return int(cl_to_lnd_scid(s))
    if 'x' in s:
        return int(x_to_lnd_scid(s))
    return int(s)

def print_route(route, lnd):
    route_str = ""
    for i in range(0,len(route.hops)):
        h = route.hops[i]
        fee = ""
        if (i > 0):
            fee = str(route.hops[i-1].fee_msat)

        route_str += " ➜ " + col_lo(print_chanid(h.chan_id).ljust(14))
        route_str += col_hi(fee.ljust(7))
        route_str += print_node(lnd.get_node_info(h.pub_key))
        route_str += "\n"
    return route_str

def print_node(node_info):
    node_str = "[%s]" % "|".join([
        col_name(node_info.node.alias),
        col_val(str(node_info.num_channels)) + 'ch',
        col_val("{:,}".format(node_info.total_capacity)) + 'sat'
    ])
    return node_str
        
def print_chanid(chan_id):
    return "%sx%sx%s" % lnd_to_cl_scid(chan_id)

def col_lo(s):
    return colored(s,'white', attrs=['dark'])

def col_hi(s):
    return colored(s,'white', attrs=['bold'])

def col_name(s):
    return colored(s,'blue', attrs=['bold'])

def col_err(s):
    return colored(s,'red', attrs=['bold'])

def col_val(s):
    return colored(s,'yellow', attrs=['bold'])
