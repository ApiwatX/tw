# thanks rcdo

# Name                         Code  Action          Description
DISPATCH =                     0  #  Recv            dispatch event
HEARTBEAT =                    1  #  Send/Recv       keepalive
IDENTIFY =                     2  #  Send            used for login
PRESENCE_UPDATE =              3  #  Send            used when other client update status event
VOICE_STATE_UPDATE =           4  #  Send            used for join/move/leave voice event
VOICE_SERVER_PING =            5  #  Send            used for voice ping
RESUME =                       6  #  Send            resume a closed connection
RECONNECT =                    7  #  Recv            used to tell client to reconnect when server restart
REQUEST_GUILD_MEMBERS =        8  #  Send            used to request guild members
INVALID_SESSION =              9  #  Recv
HELLO =                        10 #  Recv            sent after connect, heartbeat rate and server debug info
HEARTBEAT_ACK =                11 #  Sent            keepalive response
GUILD_SYNC =                   12 #  Recv
DM_UPDATE =                    13 #  Send            dm features
LAZY_REQUEST =                 14 #  Send
LOBBY_CONNECT =                15 #  Unknown
LOBBY_DISCONNECT =             16 #  Unknown
LOBBY_VOICE_STATES_UPDATE =    17 #  Recv
STREAM_CREATE =                18 #  Unknown
STREAM_DELETE =                19 #  Unknown
STREAM_WATCH =                 20 #  Unknown
STREAM_PING =                  21 #  Send
STREAM_SET_PAUSED =            22 #  Unknown
REQUEST_APPLICATION_COMMANDS = 24 #  Send            request application/bot slash cmds

opcodes = {0: "DISPATCH", 1: "HEARTBEAT", 2: "IDENTIFY", 3: "PRESENCE_UPDATE", 4: "VOICE_STATE_UPDATE", 5: "VOICE_SERVER_PING", 6: "RESUME", 7: "RECONNECT", 8: "REQUEST_GUILD_MEMBERS", 9: "INVALID_SESSION", 10: "HELLO", 11: "HEARTBEAT_ACK", 12: "GUILD_SYNC", 13: "DM_UPDATE", 14: "LAZY_REQUEST", 15: "LOBBY_CONNECT", 16: "LOBBY_DISCONNECT", 17: "LOBBY_VOICE_STATES_UPDATE", 18: "STREAM_CREATE", 19: "STREAM_DELETE", 20: "STREAM_WATCH", 21: "STREAM_PING", 22: "STREAM_SET_PAUSED", 23: "UNKNOWN", 24: "REQUEST_APPLICATION_COMMANDS"}

def opcodeToClean(opcode):
	if not isinstance(opcode, int): return None #raise Exception("Opcodes must be integer")
	if not opcode in opcodes: return None #raise Exception("Opcode not exists or not impl")
	return opcodes[opcode]