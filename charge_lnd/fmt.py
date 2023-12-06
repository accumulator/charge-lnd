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

def print_node(node_info):
    items = []
    if node_info.node.alias != '':
        items.append(col_name(node_info.node.alias))
    items.append(col_lo(node_info.node.pub_key))
    node_str = "[%s]" % "|".join(items)
    return node_str
        
def print_chanid(chan_id):
    return "%sx%sx%s" % lnd_to_cl_scid(chan_id)

def col_lo(s):
    return str(colored(str(s),'white', attrs=['dark']))

def col_hi(s):
    return str(colored(str(s),'white', attrs=['bold']))

def col_name(s):
    return str(colored(str(s),'blue', attrs=['bold']))

def col_err(s):
    return str(colored(str(s),'red', attrs=['bold']))

def col_val(s):
    return str(colored(str(s),'yellow', attrs=['bold']))
