import base64
import gzip
import json
import sys

import msgpack
from Crypto.Cipher import AES


def decrypt(encrypted):
    mode = AES.MODE_CBC
    ss2 = base64.b64decode(encrypted)
    vi = b'ha4nBYA2APUD6Uv1'
    key = ss2[-32:]
    ss2 = ss2[:-32]
    cryptor = AES.new(key, mode, vi)
    plain_text = cryptor.decrypt(ss2)
    try:
        return msgpack.unpackb(plain_text, strict_map_key=False)
    except msgpack.ExtraData as err:
        return err.unpacked['data']


def gzip_zip_base64(content):
    bytes_com = gzip.compress(str(content).encode("utf-8"))
    base64_data = base64.b64encode(bytes_com)
    back = str(base64_data.decode())
    return back


def gzip_unzip_base64(content):
    base64_data = base64.b64decode(content)
    bytes_decom = gzip.decompress(base64_data)
    str_unzip = bytes_decom.decode()
    return str_unzip


def load_from_htm(path):
    with open(path, 'rb') as f:
        s = f.read()
    return decrypt(s)


def unit_trans(unit):
    eq_stats = ''
    for i in range(6):
        eq_stats += str(unit['equip_slot'][i]['is_slot'])
    data = {'e': eq_stats,
            'p': unit['promotion_level'],
            'r': unit['unit_rarity'],
            'u': hex(int(unit['id'] / 100))[2:],
            't': 'false'}
    if len(unit['unique_equip_slot']):
        data['q'] = str(unit['unique_equip_slot'][0]['enhancement_level'])
    else:
        data['q'] = ''
    return data


def unit_list_trans(unit_list):
    data = []
    for unit in unit_list:
        data.append(unit_trans(unit))
    return data


def check_trace(trace_str, unit):
    try:
        rank, lim = trace_str.split('.')
    except ValueError:
        return True
    if unit['p'] != int(rank):
        return unit['p'] < int(rank)
    for eq_count in range(6, 0, -1):
        if unit['e'][[1, 3, 5, 4, 2, 0][eq_count - 1]] == '1':
            return eq_count <= int(lim)
    return True


def unit_trace_sync(unit_list, ref_list):
    trace_dict = {}
    synced_list = []
    for unit in ref_list:
        trace_dict[unit['u']] = unit['t']
    for unit in unit_list:
        if unit['u'] in trace_dict.keys():
            if check_trace(trace_dict[unit['u']], unit):
                unit['t'] = trace_dict[unit['u']]
        synced_list.append(unit)
    return synced_list


def equip_list_trans(equip_list):
    equip_data = []
    tmp = {}
    rate = {113: 5, 123: 5, 114: 30, 124: 20, 115: 35, 125: 25, 116: 0, 126: 0}  # k:type+rarity v:whole-piece rate
    equip_list.sort(key=lambda eq: eq['id'])
    for equip in equip_list:
        eq_type = int(equip['id'] / 1e4)  # 10-equip 11-fragment 12-blueprint 13-unique_equip 14-p_heart
        rarity = int(equip['id'] / 1e3) % 10  # 0heart 1Blue 2Bronze 3Silver 4Gold 5Purple 6Red
        if eq_type == 13 or rarity in range(1, 3):
            continue
        sid = equip['id'] % 10000
        count = equip['stock']
        if eq_type == 10 or equip['id'] == 140000:
            tmp[sid] = count
        else:
            if equip['id'] == 140001 and 0 in tmp.keys():
                count += tmp[0] * 10
            if sid in tmp.keys():
                count += tmp[sid] * rate[eq_type * 10 + rarity]
            data = {'c': hex(count)[2:], 'e': hex(equip['id'])[2:], 'a': str(int(count != 0))}
            equip_data.append(data)
    return equip_data


def make_library_dict(game_data):
    lib_dict = [unit_list_trans(game_data['unit_list']), equip_list_trans(game_data['user_equip'])]
    return lib_dict


def enc_library_dict(data):
    return gzip_zip_base64(json.dumps(data, separators=(',', ':')))


if __name__ == '__main__':
    p = sys.argv[1]
    o = load_from_htm(p)
    ud = unit_list_trans(o['unit_list'])
    if len(sys.argv) > 2:
        ref = json.loads(gzip_unzip_base64(sys.argv[2]))[0]
        ud = unit_trace_sync(ud, ref)
    ed = equip_list_trans(o['user_equip'])
    e = enc_library_dict([ud, ed])
    print(e)
