import sys, os, ctypes
path = os.getcwd()+"\\lib\\"
sys.path.append(path)
os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
import screenshot
import threading
import datetime as dt
from lib import pybass as bass
from lib import pybassflac, pybasswma, pybassopus,pybass_aac, pybass_alac, pybass_ape, pybass_tta, pytags
from lib import pybassfx as bass_fx
from lib import pybassmix as bass_mix
from lib import libmpv as mpv
from enum import Enum

class state(Enum):
    PLAYER_STATE_PLAYING = 1
    PLAYER_STATE_PAUSED = 0
    PLAYER_STATE_stopped = -1
    PLAYER_STATE_ENDED = 2
    VOLUME_UP = 1
    VOLUME_DOWN = -1

class wmp_device:
    def __init__(self,index,name,driver):
        self.index = index
        self.name = name
        self.driver = driver


WMP_STATE_PLAYING = state.PLAYER_STATE_PLAYING
WMP_STATE_PAUSED = state.PLAYER_STATE_PAUSED
WMP_STATE_STOPPED = state.PLAYER_STATE_stopped
WMP_STATE_ENDED = state.PLAYER_STATE_ENDED
WMP_VOLUME_UP = state.VOLUME_UP
WMP_VOLUME_DOWN = state.VOLUME_DOWN

effect_dx_corus = bass.BASS_FX_DX8_CHORUS
effect_dx_comprusor = bass.BASS_FX_DX8_COMPRESSOR
effect_dx_distortion = bass.BASS_FX_DX8_DISTORTION
effect_dx_echo = bass.BASS_FX_DX8_ECHO
effect_dx_flanger = bass.BASS_FX_DX8_FLANGER
effect_dx_gargle = bass.BASS_FX_DX8_GARGLE
effect_dx_reverb2 = bass.BASS_FX_DX8_I3DL2REVERB
effect_dx_parameq = bass.BASS_FX_DX8_PARAMEQ
effect_dx_reverb = bass.BASS_FX_DX8_REVERB
effect_rotate = bass_fx.BASS_FX_BFX_ROTATE
effect_echo = bass_fx.BASS_FX_BFX_ECHO
effect_flanger = bass_fx.BASS_FX_BFX_FLANGER
effect_volume = bass_fx.BASS_FX_BFX_VOLUME
effect_peakeq = bass_fx.BASS_FX_BFX_PEAKEQ
effect_mix = bass_fx.BASS_FX_BFX_MIX
effect_damp = bass_fx.BASS_FX_BFX_DAMP
effect_autowah =bass_fx.BASS_FX_BFX_AUTOWAH
effect_echo2 = bass_fx.BASS_FX_BFX_ECHO2
effect_phaser = bass_fx.BASS_FX_BFX_PHASER
effect_corus = bass_fx.BASS_FX_BFX_CHORUS
effect_distortion = bass_fx.BASS_FX_BFX_DISTORTION
effect_compressor2 = bass_fx.BASS_FX_BFX_COMPRESSOR2
effect_volume_env = bass_fx.BASS_FX_BFX_VOLUME_ENV
effect_bqf = bass_fx.BASS_FX_BFX_BQF
effect_echo4 = bass_fx.BASS_FX_BFX_ECHO4
effect_pitch_shift = bass_fx.BASS_FX_BFX_PITCHSHIFT
effect_freeverb = bass_fx.BASS_FX_BFX_FREEVERB

class effect:

    def __init__(self,handle,parameters,params):
        self.handle = handle()
        self.pointer = ctypes.byref(self.handle)
#        ctypes.cast(self.pointer,ctypes.c_void_p)
        self.params = params
        self.parameters = parameters
        self.__dict__.update(self.parameters)
        for i,k in zip(list(self.parameters.values()),list(self.params.values())):
            self.struct.i = k

class dx_chorus(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_CHORUS
        self.params = params
        self.parameters = {"wet_dry_mix": "fWetDryMix", "depth": "fDepth", "feedback": "fFeedback", "frequency": "fFrequency",
                           "waveForm": "lWaveform", "delay": "fDelay", "phase": "lPhase"}
        super().__init__(self.struct, self.parameters, self.params)

class dx_compressor(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_COMPRESSOR
        self.params = params
        self.parameters = {"gain": "fGain", "attack": "fAttack", "release": "fRelease", "threshold": "fThreshold",
                           "ratio": "fRatio", "predelay": "fPredelay"}
        super().__init__(self.struct, self.parameters, self.params)

class dx_distortion(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_DISTORTION
        self.params = params
        self.parameters = {"gain": "fGain", "edge": "fEdge", "postEQCenterFrequency": "fPostEQCenterFrequency",
                           "postEQBandwidth": "fPostEQBandwidth", "preLowpassCutoff": "fPreLowpassCutoff"}
        super().__init__(self.struct, self.parameters, self.params)

class dx_echo(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_ECHO
        self.params = params
        self.parameters = {"wet_dry_mix": "fWetDryMix", "feedback": "fFeedback", "leftDelay": "fLeftDelay",
                           "rightDelay": "fRightDelay",}# "panDelay": "lPanDelay"}
        super().__init__(self.struct, self.parameters, self.params)

class dx_flanger(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_FLANGER
        self.params = params
        self.parameters = {"wet_dry_mix": "fWetDryMix", "depth": "fDepth", "feedback": "fFeedback",
                           "frequency": "fFrequency", "waveForm": "lWaveform", "delay": "fDelay", "phase": "lPhase"}
        super().__init__(self.struct, self.parameters, self.params)

class dx_gargle(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_GARGLE
        self.params = params
        self.parameters = {"rateHz": "dwRateHz", "waveShape": "dwWaveShape"}
        super().__init__(self.struct, self.parameters, self.params)

class dx_reverb2(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_I3DL2REVERB
        self.params = params
        self.parameters = {"room": "lRoom", "roomHF": "lRoomHF", "roomRolloffFactor": "flRoomRolloffFactor",
                           "decayTime": "flDecayTime", "decayHFRatio": "flDecayHFRatio", "reflections": "lReflections",
                           "reflectionsDelay": "flReflectionsDelay", "reverb": "lReverb", "reverbDelay": "flReverbDelay",
                           "diffusion": "flDiffusion", "density": "flDensity", "hfReference": "flHFReference"}
        super().__init__(self.struct, self.parameters, self.params)

class dx_parameq(effect):

    def __init__(self, params):
        self.struct = bass.BASS_DX8_PARAMEQ
        self.params = params
        self.parameters = {"center": "fCenter", "bandwidth": "fBandwidth", "gain": "fGain"}
        super().__init__(self.struct, self.parameters, self.params)


class fx_rotate(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_ROTATE
        self.params = params
        self.parameters = {"rate": "fRate", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_echo(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_ECHO
        self.params = params
        self.parameters = {"level": "fLevel", "delay": "lDelay"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_flanger(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_FLANGER
        self.params = params
        self.parameters = {"wetdry": "fWetDry", "speed": "fSpeed", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_volume(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_VOLUME
        self.params = params
        self.parameters = {"channel": "lChannel", "volume": "fVolume"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_peakeq(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_PEAKEQ
        self.params = params
        self.parameters = {"band": "lBand", "bandwidth": "fBandwidth", "q": "fQ", "center": "fCenter", "gain": "fGain", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_lpf(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_LPF
        self.params = params
        self.parameters = {"resonance": "fResonance", "cutoff_frequency": "fCutOffFreq", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_mix(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_MIX
        self.params = params
        self.parameters = {"channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_damp(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_DAMP
        self.params = params
        self.parameters = {"target": "fTarget", "quiet": "fQuiet", "rate": "fRate` ", "gain": "fGain", "delay": "fDelay", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_autowah(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_AUTOWAH
        self.params = params
        self.parameters = {"drymix": "fDryMix", "wetmix": "fWetMix", "feedback": "fFeedback", "rate": "fRate", "range": "fRange",
               "freq": "fFreq", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_echo2(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_ECHO2
        self.params = params
        self.parameters = {"drymix": "fDryMix", "wetmix": "fWetMix", "feedback": "fFeedback", "delay": "fDelay", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_phaser(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_PHASER
        self.params = params
        self.parameters = {"drymix": "fDryMix", "wetmix": "fWetMix", "feedback": "fFeedback", "rate": "fRate", "range": "fRange",
               "freq": "fFreq", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)


class fx_chorus(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_CHORUS
        self.params = params
        self.parameters = {"drymix": "fDryMix", "wetmix": "fWetMix", "feedback": "fFeedback", "min_sweep": "fMinSweep",
               "max_sweep": "fMaxSweep", "rate": "fRate", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_compressor(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_COMPRESSOR
        self.params = params
        self.parameters = {"threshold": "fThreshold", "attack_time": "fAttacktime", "release_time": "fReleasetime", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_distortion(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_DISTORTION
        self.params = params
        self.parameters = {"drive": "fDrive", "dry_mix": "fDryMix", "wet_mix": "fWetMix", "feedback": "fFeedback", "volume": "fVolume", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_compressor2(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_COMPRESSOR2
        self.params = params
        self.parameters = {"gain": "fGain", "threshold": "fThreshold", "ratio": "fRatio", "attack": "fAttack", "release": "fRelease", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_volume_env(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_VOLUME_ENV
        self.params = params
        self.parameters = {"channel": "lChannel", "node_count": "lNodeCount", "nodes": "pNodes", "follow": "bFollow"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_bqf(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_BQF
        self.params = params
        self.parameters = {"filter": "lFilter", "center": "fCenter", "gain": "fGain", "bandwidth": "fBandwidth", "q": "fQ", "s": "fS", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_echo4(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_ECHO4
        self.params = params
        self.parameters = {"dry_mix": "fDryMix", "wet_mix": "fWetMix", "feedback": "fFeedback", "delay": "fDelay"}#, "stereo": "bStereo", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_pitchshift(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_PITCHSHIFT
        self.params = params
        self.parameters = {"pitch_shift": "fPitchShift", "semitones": "fSemitones", "fft_size": "lFFTsize", "osamp": "lOsamp"}#, "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)

class fx_freeverb(effect):

    def __init__(self, params):
        self.struct = bass_fx.BASS_BFX_FREEVERB
        self.params = params
        self.parameters = {"dry_mix": "fDryMix", "wet_mix": "fWetMix", "room_size": "fRoomSize", "damp": "fDamp", "width": "fWidth"}#, "mode": "lMode", "channel": "lChannel"}
        super().__init__(self.struct, self.parameters, self.params)


class Player:
    def __init__(self):
        self.plugins = {"alac":path+"bassalac.dll","tta":path+"bass_tta.dll","ape":path+"bassape.dll","flac":path+"bassflac.dll","opus":path+"bassopus.dll","wma":path+"basswma.dll","aac":path+"bass_aac.dll","fx":path+"bassfx.dll","mix":path+"bassmix.dll","tags":path+"tags.dll"}
        self.plugings = {}
        self.device = self.getDevice
        self.devices = self.getDevices
        self.load = self.loader
        self.player = self.playerInst
        self.threeD = self.threeDfx
        self.fx = self.audioFx
        self.mixer = self.getmixer

        bass.BASS_Init(-1,48000,0,0,0)
        for plugin in self.plugins:
            self.plugins[plugin] = bass.BASS_PluginLoad(plugin.encode("utf-8"),0)

    def getDeviceInfo(self,index):
        device_info = bass.BASS_DEVICEINFO()
        bass.BASS_GetDeviceInfo(index,device_info)
        return wmp_device(index,device_info.name,device_info.driver)

    def getDevice(self):
        return self.getDeviceInfo(bass.BASS_GetDevice())

    def getDevices(self):
        device = 0
        devices = []
        device_info = bass.BASS_DEVICEINFO()
        searching = True
        while (searching==True):
            d = self.getDeviceInfo(device)
            if d.name is not None:
                devices.append(d)
                device+=1
            else:
                searching = False
                break
        return devices

    def setDevice(self,device):
        bass.BASS_SetDevice(device)


    def loader(self):
        return self.Loader(self)
    def playerInst(self):
        return self.Player(self)
    def threeDfx(self):
        return self.threed(self)
    def audioFx(self):
        return self.Fx(self)
    def getmixer(self):
        return self.Mixer(self)

    def close(self):
        for plugin in self.plugins: bass.BASS_PluginFree(self.plugins[plugin])
        bass.BASS_Free


    class Loader:
        def __init__(self, instance):
            self.playerInstance = instance
            self.formats = ["opus","flac","aac","m4a","wma","ape","tta","alac"]



        def file(self,source,inst,memoryLoad=False,mono=False,looped=False,threeD=False,mutemax=False,audioFloat=False):
            if source[-4:] in self.formats: src = bass.BASS_StreamCreateFile(memoryLoad, source.encode("utf-8"), 0, 0,bass.BASS_SAMPLE_FX)
            else: src = bass.BASS_StreamCreateFile(memoryLoad, source, 0, 0,bass.BASS_UNICODE|bass.BASS_SAMPLE_FX)
            if mono == True : bass.BASS_ChannelFlags(src,bass.BASS_SAMPLE_MONO,bass.BASS_SAMPLE_MONO)
            if looped == True: bass.BASS_ChannelFlags(src,bass.BASS_SAMPLE_LOOP,bass.BASS_SAMPLE_LOOP)
            if mutemax == True: bass.BASS_ChannelFlags(src,bass.BASS_SAMPLE_MUTEMAX,bass.BASS_SAMPLE_MUTEMAX)
            if threeD==True: bass.BASS_ChannelFlags(src,bass.BASS_SAMPLE_3D,bass.BASS_SAMPLE_3D)
            if audioFloat==True: bass.BASS_ChannelFlags(src,bass.BASS_SAMPLE_FLOAT,bass.BASS_SAMPLE_FLOAT)
            inst.handles[src] = {}
            inst.handles[src]["muted"] = False
            return src

        def fuck(self):
            pass
        def url(self,source,inst,memoryLoad=False):
#            if source[-4:] in self.formats: src = bass.BASS_StreamCreateURL(source.encode("utf-8"), 0, 0,0)
            sf = ctypes.create_string_buffer(source.encode('utf-8') )
            src = bass.BASS_StreamCreateURL(sf, 0,0,bass.DOWNLOADPROC(),0)
            inst.handles[src] = {}
            inst.handles[src]["muted"] = False
            return src





    class Player:
        def __init__(self,instance):
            self.pInstance = instance
            self.handles = {}
            
        def mute(self,handle):
            if self.handles[handle]["muted"] == False:
                self.handles[handle]["vol"] = round(self.getvolume(handle),2)
                self.setvolume(handle,0)
                self.handles[handle]["muted"] = True
            elif self.handles[handle]["muted"] == True:
                self.setvolume(handle,round(self.getvolume(handle)*100,2))
                self.handles[handle]["muted"] = False

        def button(self,handle):
            pbs = bass.BASS_ChannelIsActive(handle)
            if pbs == bass.BASS_ACTIVE_PAUSED or pbs == bass.BASS_ACTIVE_STOPPED:
                bass.BASS_ChannelPlay(handle,False)
            elif pbs == bass.BASS_ACTIVE_PLAYING:
                bass.BASS_ChannelPause(handle)

        def stop(self,handle):
            bass.BASS_ChannelStop(handle)



        def getvolume(self,handle):
            val=ctypes.c_float()
            bass.BASS_ChannelGetAttribute(handle,bass.BASS_ATTRIB_VOL,ctypes.pointer(val))
            if self.handles[handle]["muted"] == False: return val.value
            elif self.handles[handle]["muted"] == True: return self.handles[handle]["vol"]


        def forword(self,handle,offset):
            pos_val = int(self.gettime(handle)["position"]+offset)
            if int(self.gettime(handle)["position"]) < int(self.gettime(handle)["length"]): pos = bass.BASS_ChannelSeconds2Bytes(handle,pos_val)
            if pos_val> int(self.gettime(handle)["length"]): pos = bass.BASS_ChannelSeconds2Bytes(handle,self.gettime(handle)["length"])
            bass.BASS_ChannelSetPosition(handle,pos,bass.BASS_POS_BYTE)


        def backword(self,handle,offset):
            pos = bass.BASS_ChannelSeconds2Bytes(handle, int(self.gettime(handle)["position"]-offset) if self.gettime(handle)["position"] > offset else 0)
            bass.BASS_ChannelSetPosition(handle,pos,bass.BASS_POS_BYTE)

        def settime(self,handle,offset):
            pos = bass.BASS_ChannelSeconds2Bytes(handle, offset)
            bass.BASS_ChannelSetPosition(handle,pos,bass.BASS_POS_BYTE)
            


        def setVolume(self, handle, vstate, offset):
            current_volume = self.getvolume(handle)
            if self.handles[handle]["muted"] == True: self.handles[handle]["muted"] = False
            if vstate == WMP_VOLUME_UP:
                new_volume = round(current_volume + offset / 100, 2)
            elif vstate == WMP_VOLUME_DOWN:
                new_volume = round(current_volume - offset / 100, 2)
            val = ctypes.c_float(new_volume)
            bass.BASS_ChannelSetAttribute(handle, bass.BASS_ATTRIB_VOL, new_volume)

        def setvolume(self,handle,offset):
            if self.handles[handle]["muted"] == True: self.handles[handle]["muted"] = False
            bass.BASS_ChannelSetAttribute(handle,bass.BASS_ATTRIB_VOL,round(offset/100,2))

        def get_length(self,handle):
           return int(bass.BASS_ChannelBytes2Seconds(handle, bass.BASS_ChannelGetLength(handle,bass.BASS_POS_BYTE)))

        def get_position(self,handle):
            return int(bass.BASS_ChannelBytes2Seconds(handle,bass.BASS_ChannelGetPosition(handle, bass.BASS_POS_BYTE)))

        def gettime(self,handle):
            audiotime = {}
            audiotime["length"] = int(bass.BASS_ChannelBytes2Seconds(handle, bass.BASS_ChannelGetLength(handle,bass.BASS_POS_BYTE)))
            audiotime["position"] = int(bass.BASS_ChannelBytes2Seconds(handle,bass.BASS_ChannelGetPosition(handle, bass.BASS_POS_BYTE)))
            audiotime["remaining"] = int(bass.BASS_ChannelBytes2Seconds(handle, bass.BASS_ChannelGetLength(handle,bass.BASS_POS_BYTE))-bass.BASS_ChannelBytes2Seconds(handle,bass.BASS_ChannelGetPosition(handle, bass.BASS_POS_BYTE)))
            return audiotime



        def state(self,handle):
            pbs = bass.BASS_ChannelIsActive(handle)
            states = {"stopped": WMP_STATE_STOPPED,"playing":WMP_STATE_PLAYING,"paused":WMP_STATE_PAUSED,"ended":WMP_STATE_ENDED}
            if pbs == bass.BASS_ACTIVE_STOPPED and self.gettime(handle)["position"] != self.gettime(handle)["length"]: return states["stopped"]
            elif pbs == bass.BASS_ACTIVE_PLAYING and self.gettime(handle)["position"] != self.gettime(handle)["length"]: return states["playing"]
            elif pbs == bass.BASS_ACTIVE_PAUSED and self.gettime(handle)["position"] != self.gettime(handle)["length"]: return states["paused"]
            elif pbs == bass.BASS_ACTIVE_STOPPED and self.gettime(handle)["position"] == self.gettime(handle)["length"]: return states["ended"]
            else: return -1


        def free(self,handle):
            if handle and handle in self.handles:
                del self.handles[handle]
                bass.BASS_StreamFree(handle)

    class threed:
        def __init(self,instance):
            self.instance = instance

        def apply(self,handle):
            bass.BASS_Apply3D(handle)

        def getListenerPosition(self,position=True,velocity=False,front=False,top=False):
            pos,vel,fro,to= bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR()
            bass.BASS_Get3DPosition(pos,vel if velocity != None else None, fro if front!= None else None, to if top != None else None)
            return pos,vel,fro,to


        def getPosition(self,handle,position=True,orientation=False,velocity=False):
            pos,orient,vel = bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR()
            bass.BASS_ChannelGet3DPosition(handle,pos, orient if orientation == True else None,vel if velocity== True else None)
            return pos, orient, vel


        def set3deEnvironment(self,handle,distanceScale,rolloff,doppler):
            bass.BASS_Set3DFactors(handle,distanceScale,rolloff,doppler)

        def setListenerPosition(self,position,velocity=None,front=None,top=None):
            pos,vel,fro,to= bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR()
            pos.x,pos.y,pos.z = position
            if front != None: fro.x,fro.y,fro.z=fro
            if velocity != None: vel.x,vel.y,vel.z=velocity
            if top != None: to.x,to.y,to.z=to
            bass.BASS_Set3DPosition(pos, vel if velocity is not None else None, fro if front is not None else None, to if top is not None else None)


        def setPosition(self,handle,position,orientation=None,velocity=None):
            pos,orient,vel = bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR(),bass.BASS_3DVECTOR()
            pos.x,pos.y,pos.z=position
            if orientation != None: orient.x, orient.y,orient.z=orientation
            if velocity != None: vel.x,vel.y,vel.z=velocity
            bass.BASS_ChannelSet3DPosition(handle, pos, orient if orientation is not None else None, vel if velocity is not None else None)


    class Mixer:
        def __init__(self,instance):
            self.instance = instance

        def create(self,inst,freq,channel=2):
            src = bass_mixer.BASS_Mixer_StreamCreate(freq,channels,0)
            if threeD==True: bass.BASS_ChannelFlags(src,bass.BASS_SAMPLE_3D,bass.BASS_SAMPLE_3D)
            if audioFloat==True: bass.BASS_ChannelFlags(src,bass.BASS_SAMPLE_FLOAT,bass.BASS_SAMPLE_FLOAT)
            inst.handles[src] = {}
            inst.handles[src]["muted"] = False
            return src

        def addChannel(self,mixer,handle):
            bass_mixer.BASS_Mixer_StreamAddChannel(mixer,handle,0)

        def removeChannel(self,handle):
            bass_mixer.BASS_Mixer_ChannelRemove(handle)


        def getChannels(self,mixer):
            channels = []
            chans = bass.BASS_Mixer_StreamGetChannels(mixer,None,0)
            bass.BASS_Mixer_StreamGetChannels(mixer,channels,chan)
            return channels

        def forword(self,mixer,inst,offset):
            for channel in self.getChannels(mixer):
                            pos = inst.get_position(channel)
                            inst.forword(channel,offset)

            

        def backword(self,mixer,inst):
            for channel in self.getChannels(mixer):
                            pos = inst.get_position(channel)
                            inst.backword(channel,offset)

        def settime(self,mixer,inst):
            for channel in self.getChannels(mixer):
                            pos = inst.get_position(channel)
                            inst.settime(channel,offset)

class fx:

    def __init__(self,handle,effect,struct,params):
        self.source = handle
        self.handle = bass.BASS_ChannelSetFX(self.source,effect,0)
        self.struct  = struct(params)
        self.setParam()

    def setParam(self,param=None,value=None):
        if param != None and value != None:
            v = [param]
            p = getattr(self.struct,param)
            setattr(self.struct.handle,p,value)
            bass.BASS_FXSetParameters(self.handle,self.struct.pointer)


    def getParam(self,param):
        if param:
            p = getattr(self.struct,param)
            bass.BASS_FXGetParameters(self.handle,ctypes.cast(self.struct.pointer,ctypes.c_void_p))
            return getattr(self.struct.handle,p)


    def remove(self):
        bass.BASS_ChannelRemoveFX(self.source,self.handle)
        del self


class video:
    def __init__(self,window=None,path=""):
        self.subtitle_formats = ["idx", "sub", "srt", "rt", "ssa", "ass", "mks", "vtt", "sup", "scc", "smi", "lrc", "pgs"]
        self.updatePosThread = False
        self.endReached = False
        self.path = path
        self.duration = 0
        self.pos  = -1
        self.window= window
        if self.window is not None:
            self.instance = mpv.MPV(wid=str(int(self.window)),ytdl=True,input_default_bindings=True)
        else:
            self.instance = mpv.MPV(ytdl=True,input_default_bindings=True)
        self.instance.script_opts["ytdl_hook-ytdl_path"]= f'{path}\\yt-dlp.exe'
        self.stopped = False
        if self.path != "":
            self.load(self.path)
            self.runtime()

    def setWindow(self,window):
        self.instance._set_property("wid", str(int(window)))

    def load(self,path):
        subtitle_file = ""
        self.duration = 0
        self.pos = -1
        self.path = path
        dir = os.path.dirname(self.path)
        filename = os.path.splitext(self.path)[0]
        self.instance.command("loadfile",self.path)
#        self.instance.play(self.path)
        for format in self.subtitle_formats:
            file_path = os.path.join(dir,f".{format}")
            if os.path.exists(file_path):
                subtitle_file = filepath
                break
        if subtitle_file != "": self.instance.sub_add(subtitle_file)
        self.runtime()
#        if "youtube" in self.path: self.instance.play(self.path)

    def runtime(self):
            if not self.updatePosThread:
                self.updatePosThread = threading.Thread(target=self.updatePos)
                self.updatePosThread.start()

    def updatePos(self):
        def on_property_change(name,value):
            if name in ("time-pos", "duration"):
                if not self.instance.pause:
                    if self.instance.time_pos is not None and self.instance.duration is not None:
                        self.pos = int(self.instance.time_pos)
                        self.duration = int(self.instance.duration)
            if self.instance.time_pos is not None and self.instance.duration is not None:
                if self.pos >= self.duration: self.endReached = True
                else: self.endReached = False
        self.instance.observe_property("time-pos", on_property_change)

    def stop(self):
        if self.instance.core_shutdown == False and self.instance.pause == False: self.instance.pause = True
        self.instance.stop()
        self.stopped = True

    def button(self):
        if self.stopped == True: self.stopped = False
        if self.instance.pause == True:
            self.endOfPlayback()
            self.instance.pause = False
        elif self.instance.pause == False:
            self.instance.pause = True

    def endOfPlayback(self):
        if self.duration >= self.pos and self.instance.time_pos is None:
            self.instance.command("loadfile",self.path)

    def mute(self):
        if self.instance.mute == True:
            self.instance.mute = False
        elif self.instance.mute == False:
            self.instance.mute = True

    def forword(self,offset):
        self.instance.seek(+offset,reference='relative')

    def backword(self,offset):
        self.instance.seek(-offset,reference='relative')
    def getvolume(self):
        return self.instance.volume

    def setvolume(self,offset):
        self.instance.volume = offset
    def setVolume(self,vstate,offset):
        current_volume = self.instance.volume
        if vstate == WMP_VOLUME_UP:
            self.instance.volume = current_volume + offset
        elif vstate == WMP_VOLUME_DOWN:
            self.instance.volume = current_volume - offset

    def settime(self,offset):
        self.instance.seek(offset,"absolute")

    def gettime(self):
        audiotime = {}
        if self.instance.core_shutdown == False:
            if self.instance.duration is not None and self.instance.time_pos is not None:
                audiotime["length"] = int(self.instance.duration) if self.instance.duration is not None else None
                audiotime["position"] = int(self.instance.time_pos) if self.instance.time_pos is not None else None
                audiotime["remaining"] = int(self.instance.duration-self.instance.time_pos) if self.instance.duration is not None else None
                return audiotime
        else: return {"length":None,"remaining":None,"position":None}

    def close(self):
        self.x = True
        self.instance.terminate()

    def state(self):
        states = {"stopped": WMP_STATE_STOPPED,"playing":WMP_STATE_PLAYING,"paused":WMP_STATE_PAUSED,"ended":WMP_STATE_ENDED}
        if self.stopped == True: return states["stopped"]
        elif self.instance.pause == False and self.endReached == False: return states["playing"]
        elif self.instance.pause == True and self.stopped == False and self.endReached == False: return states["paused"]
        elif self.instance.pause == True and self.endReached == True or self.instance.pause == False and self.endReached == True: return states["ended"]
        else: return -1

    def fullScreen(self,state):
        self.instance.fullscreen = state

    def fullscreen(self):
        return self.instance.fullscreen

    def playbackSpeed(self,speed):
        self.instance.speed = speed
   
    def setResolution(self,width,height):
        self.instance.vf = f"scale={width}:{height}"

    def getDevices(self):
        return self.instance.audio_device_list

    def getDevice(self):
        return self.instance.audio_device

    def setDevice(self,device):
        self.instance.audio_device = device

    def screenshot(self,path,format,instance):
        if path is not None and self.pos is not None and self.duration is not None:
            filedate = str(dt.datetime.now().strftime("%y-%d-%m-%I-%M-%S%p"))
            p = path+"screenshot"+filedate+format
        screenshot.take(self.path,p,self.pos,instance)
