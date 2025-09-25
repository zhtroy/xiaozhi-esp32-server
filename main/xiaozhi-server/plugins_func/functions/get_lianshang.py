import requests
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info

TAG = __name__
logger = setup_logging()

"""
/aiApi/situation/device?producerId=11&qr=CXR101079  get  查询设备
/aiApi/situation/storage?producerId=11&storageName=001  get  查询暂存间
/aiApi/mgTerminal/sensorData?producerId=211&storageName=001&terminalNo=00000000203&pageSize=20 产废方传感器数据
    产废方ID producerId
    传感器类型type 1电流2空气质量3噪音4可燃气体5地磅 页
    危废间名称storageName
    终端编号terminalNo
    面数据大小pageSize 不传默认25
/aiApi/deviceMod/command  post请求 下发传感器命令 
    产废方ID producerId
    传感器设备类型type 设备类型 1 液位桶 2称重贮存桶  11电流12空气质量；13噪音 14可燃气体 15（BM01）称重模块 16风机
    开关值 disjunctor 0关1开
    危废间名称storageName
"""

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    )
}

GET_ROOM_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_room",
        "description": (
            "获取危废间内全部设备的信息，用户应提供危废间编号n， 比如用户说“查询1号危废间的信息”,或者说“1号房间里有些啥?”,返回参数是：1"
            "但是由于语音识别不准，请将类似危废间读音的词都识别为危废间，比如weifei间，位飞间，微飞间,卫生间,房间等"
            "不要编造不存在的信息"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "room_number": {
                    "type": "int",
                    "description": "危废间编号",
                }
            },
        },
    },
}

def _parse_devicelist(data):
    roomstr = ""
    for room in data:
        if room["jack"] == 1:  #油桶
            roomstr += f"{room['qr']}号设备已装了{room['massNum']}升{room['preset']['name']}，占设备容量的{room['dataValue']}%\n"
        else:
            roomstr += f"{room['qr']}号设备已装了{room['dataValue']/1000.0}kg{room['preset']['name']}\n"
    return roomstr

def fetch_room_info(room_number, api_host, conn):
    try:
        url = f"https://{api_host}/aiApi/situation/storage?producerId={conn.headers.get('producer-id')}&storageName={room_number:03d}"
        data = requests.get(url, headers=HEADERS).json()['data']
        if len(data) == 0:
            return "没找到哦，请检查危废间编号"
        infostr = f"{data[0]['producerName']}的{room_number}号危废间有{len(data)}个设备\n"
        infostr += _parse_devicelist(data)
    except Exception as e:
        logger.bind(tag=TAG).error(f"危废间信息格式有误: {e}")
        return f"危废间信息格式有误 {e}"

    return infostr

@register_function("get_room", GET_ROOM_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_room(conn, room_number: int = 0):
    api_host = conn.config["plugins"]["get_lianshang"].get("api_host", "api.scwego.com")
    infostr = fetch_room_info(room_number, api_host, conn)

    return ActionResponse(Action.RESPONSE, infostr, infostr)


GET_DEVICE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_device",
        "description": (
            "获取某个设备（包括机油桶，称重桶，地磅等）的信息，用户应提供设备编号n， 比如用户说“查询42号设备的信息”,或者说“42号地磅有多重”,返回参数是数字：42"
            "不要编造不存在的信息"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_number": {
                    "type": "int",
                    "description": "设备编号",
                }
            },
        },
    },
}

def fetch_device_info(device_number, api_host, conn):
    try:
        url = f"https://{api_host}/aiApi/situation/device?producerId={conn.headers.get('producer-id')}&qr={device_number}"
        data = requests.get(url, headers=HEADERS).json()['data']
        if len(data) == 0:
            return "没找到哦，请检查设备编号"
        infostr = f"我在{data[0]['producerName']}找到了{len(data)}个设备\n"
        infostr += _parse_devicelist(data)
    except Exception as e:
        logger.bind(tag=TAG).error(f"危废间信息格式有误: {e}")
        return f"危废间信息格式有误 {e}"

    return infostr

@register_function("get_device", GET_DEVICE_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_device(conn, device_number: int = 0):
    api_host = conn.config["plugins"]["get_lianshang"].get("api_host", "api.scwego.com")
    infostr = fetch_device_info(device_number, api_host, conn)

    return ActionResponse(Action.RESPONSE, infostr, infostr)


GET_AIR_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_air",
        "description": (
            "通过传感器获取空气质量（包括TVOC,CO2，PM2.5,PM10等）的信息，用户应提供危废间编号n， 比如用户说“查询1号危废间的空气质量”,或者说“1号房间空气怎么样”,返回参数是数字：1"
            "不要编造不存在的信息"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "room_number": {
                    "type": "int",
                    "description": "危废间编号",
                },
            },
        },
    },
}

def fetch_air_info(room_number, api_host, conn):
    try:
        url = f"https://{api_host}/aiApi/mgTerminal/sensorData?producerId={conn.headers.get('producer-id')}&storageName={room_number:03d}&type=12&pageSize=1"
        data = requests.get(url, headers=HEADERS).json()['data']
        if len(data) == 0:
            return "没找到该危废间的空气质量信息"
        infostr = f"{room_number}号危废间空气质量如下:\n{data}"
        infostr += "总结一下上面的空气质量数据，只用报TVOC的量"
    except Exception as e:
        logger.bind(tag=TAG).error(f"危废间信息格式有误: {e}")
        return f"危废间信息格式有误 {e}"

    return infostr

@register_function("get_air", GET_AIR_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_air(conn, room_number: int = 0):
    api_host = conn.config["plugins"]["get_lianshang"].get("api_host", "api.scwego.com")
    infostr = fetch_air_info(room_number, api_host, conn)

    # return ActionResponse(Action.RESPONSE, infostr, infostr)
    return ActionResponse(Action.REQLLM, infostr, None)

SET_DEVICE_ONOFF_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "set_device_onoff",
        "description": (
            "控制危废间内的某个设备的开关，用户应提供危废间编号n和开关状态（0：关闭，1：打开）以及设备类型"
            "（1-液位桶 2-称重贮存桶  11-电流 12-空气质量 13-噪音 14-可燃气体 15-称重模块 16-排风扇）"
            "比如用户说“打开1号危废间的排风扇”，返回参数是：'room_number=1,device_type=16,onoff=1"
            "比如用户说“关闭1号危废间的排风扇”，返回参数是：'room_number=1,device_type=16,onoff=0"
            "比如用户说“把42号房间的排风扇关了”，返回参数是：'room_number=42,device_type=16,onoff=0"
            "比如用户说“把42号排风扇打开”，返回参数是：'room_number=42,device_type=16,onoff=1"
            "但是由于语音识别不准，请将类似危废间读音的词都识别为危废间，比如weifei间，位飞间，微飞间,卫生间,房间等"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "room_number": {
                    "type": "int",
                    "description": "危废间编号",
                },
                "device_type": {
                    "type": "int",
                    "description": "返回设备类型",
                },
                "onoff": {
                    "type": "int",
                    "description": "返回开关指令，0：关闭，1：打开",
                }
            },
        },
    },
}

def set_room_device_onoff(room_number,device_type,onoff,api_host,conn):
    url = f"https://{api_host}/aiApi/deviceMod/command"
    try:
        if device_type not in [16]:
            return "该设备不支持语音控制"
        data = {
            "producerId": conn.headers.get('producer-id'),
            "type": device_type,
            "disjunctor": onoff,
            "storageName": f"{room_number:03d}"
        }
        result = requests.post(url,json=data).json()
        if result["code"] == 200:
            return "指令已发送"
        else:
            return f"操作失败,msg={result['msg']}"
    except Exception as e:
        logger.bind(tag=TAG).error(f"危废间信息格式有误: {e}")
        return f"危废间信息格式有误 {e}"

@register_function("set_device_onoff", SET_DEVICE_ONOFF_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def set_device_onoff(conn, room_number,device_type,onoff):
    api_host = conn.config["plugins"]["get_lianshang"].get("api_host", "api.scwego.com")
    infostr = set_room_device_onoff(room_number,device_type,onoff,api_host,conn)

    return ActionResponse(Action.RESPONSE, infostr, infostr)
