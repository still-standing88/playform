import wmp

audio = {"echo": {
"name": "echo",
"handle": wmp.effect_dx_echo,
"struct": wmp.dx_echo,
"values": {
"wet_dry_mix":{"min":0,"max":100,"offset":5,"def":50},
"feedback":{"min":0,"max":100,"offset":5,"def":50},
"leftDelay":{"min":1,"max":2000,"offset":50,"def":500},
"rightDelay":{"min":1,"max":2000,"offset":50,"def":500},
},
"parameters": {"wet_dry_mix":50,"feedback":50,"leftDelay":500,"rightDelay":500}
},
"reverb": {
"name": "reverb",
"handle": wmp.effect_dx_reverb2,
"struct": wmp.dx_reverb2,
"values": {
"room":{"min":-10000,"max":0,"offset":100,"def":-1000},
"roomHF":{"min":-10000,"max":0,"offset":100,"def":-100},
"roomRolloffFactor":{"min":0,"max":10,"offset":1,"def":0},
"decayTime":{"min":0,"max":20,"offset":1,"def":1},
#"decayHFRatio":{"min":0,"max":2,"offset":0.5,"def":1},
"reflections":{"min":-10000,"max":1000,"offset":100,"def":-2602},
#"reflectionsDelay":{"min":0,"max":0.3,"offset":0.1,"def":0.07},
"reverb":{"min":-10000,"max":200,"offset":100,"def":200},
#"reverbDelay":{"min":0,"max":0.1,"offset":0.01,"def":0},
"diffusion":{"min":0,"max":100,"offset":1,"def":100},
"density":{"min":0,"max":100,"offset":1,"def":100},
"hfReference":{"min":20,"max":20000,"offset":100,"def":5000},
},
"parameters": {"room":-1000,"roomHF":-100,"roomRolloffFactor":0.0,"decayTime":1.49,"decayHFRatio":0.83,"reflections":2602,"reflectionsDelay":0.3,"reverb":200,"reverbDelay":0.011,"diffusion":100,"dencity":100,"hfReference":5000}
},
"distortion": {
"name": "distortion",
"handle": wmp.effect_dx_distortion,
"struct": wmp.dx_distortion,
"values": {
"gain":{"min":-60,"max":0,"offset":1,"def":-18},
"edge":{"min":0,"max":100,"offset":1,"def":15},
"postEQCenterFrequency":{"min":100,"max":8000,"offset":100,"def":2400},
"postEQBandwidth":{"min":100,"max":8000,"offset":100,"def":2400},
"preLowpassCutoff":{"min":100,"max":8000,"offset":100,"def":2400},
},
"parameters": {"wet_dry_mix":50,"feedback":50,"leftDelay":500,"rightDelay":500}
}
}
old = {
"echo": {
"name": "echo",
"handle": wmp.effect_echo4,
"struct": wmp.fx_echo4,
"values": {
"dry_mix":{"min":-2.000,"max":2.000,"offset":0.050,"def":0.000},
"wet_mix":{"min":-2.000,"max":2.000,"offset":0.050,"def":0.000},
"feedback":{"min":-1.000,"max":1.000,"offset":0.050,"def":0.000},
"delay":{"min":0.000,"max":1.000,"offset":0.050,"def":0.000}
},
"parameters": {"dry_mix":0.000,"wet_mix":0.000,"feedback":0.500,"delay":0.000}
},
"reverb": {
"name": "reverb",
"handle": wmp.effect_freeverb,
"struct": wmp.fx_freeverb,
"values": {
"dry_mix":{"min":0.000,"max":2.000,"offset":0.050,"def":0.000},
"wet_mix":{"min":0.000,"max":3.000,"offset":0.050,"def":1.000},
"room_size":{"min":0.000,"max":1.000,"offset":0.050,"def":0.500},
"damp":{"min":0.000,"max":1.000,"offset":0.050,"def":0.500},
"width":{"min":0.000,"max":1.000,"offset":0.050,"def":1.000}
},
"parameters": {"dry_mix":0.000,"wet_mix":1.000,"room_size":0.500,"damp":0.500,"width":1.000}
},
"pitch shift": {
"name": "pitch shift",
"handle": wmp.effect_pitch_shift,
"struct": wmp.fx_pitchshift,
"values": {
"pitch_shift":{"min":0.500,"max":2.000,"offset":0.050,"def":1.000},
"semitones":{"min":0.000,"max":0.000,"offset":0.000,"def":0.000},
"fft_size":{"min":1024,"max":8192,"offset":1024,"def":2048},
"osamp":{"min":4,"max":32,"offset":1,"def":8},
},
"parameters": {"pitch_shift":1.000,"semitones":0,"fft_size":2048,"osamp":8}
},
"distortion": {
"name": "distortion",
"handle": wmp.effect_distortion,
"struct": wmp.fx_distortion,
"values": {
"drive":{"min":0.000,"max":5.000,"offset":0.250,"def":0.000},
"dry_mix":{"min":-5.000,"max":5.000,"offset":0.250,"def":0.000},
"wet_mix":{"min":-5.000,"max":5.000,"offset":0.250,"def":0.000},
"feedback":{"min":-1.000,"max":1.000,"offset":0.050,"def":0.000},
"volume":{"min":0.000,"max":2.000,"offset":0.025,"def":1.000}
},
"parameters": {"drive":2.500,"dry_mix":0.000,"wet_mix":0.000,"feedback":0.000,"volume":1.000,}
}
}

video = {
"echo":{
"name":"aecho",
"values": {
"in_gain":{"min":0.00,"max":1.00,"offset":0.05,"def":0.60,"type":"numeric"},
"out_gain":{"min":0.00,"max":1.00,"offset":0.05,"def":0.30,"type":"numeric"},
"delays":{"min":0,"max":90000,"offset":1000,"def":1000,"type":"numeric"},
"decays":{"min":0.00,"max":1.00,"offset":0.05,"def":0.50,"type":"numeric"}
},
"filter":"audio"
},
"delay":{
"name":"adelay",
"values": {
"delays":{"min":100,"max":10000,"offset":100,"def":1000,"type":"numeric"}
},
"filter":"audio"
},
"tempo/time stretch":{
"name":"scaletempo",
"values": {
"scale":{"min":1,"max":25,"offset":1,"def":1,"type":"numeric"},
"speed":{"values":["pitch","none"],"type":"textual"}
},
"filter":"video"
},
"pitch":{
"name":"rubberband",
"values": {
"pitch-scale":{"min":1.0,"max":100.0,"offset":1.0,"def":1.0,"type":"numeric"},
"engine":{"values":["faster","finer"],"type":"textual"}
},
"filter":"video",
"special":"@rb:"
},
"chorus":{
"name":"achorus",
"values": {
"in_gain":{"min":0.00,"max":1.00,"offset":0.05,"def":0.60,"type":"numeric"},
"out_gain":{"min":0.00,"max":1.00,"offset":0.05,"def":0.30,"type":"numeric"},
"delays":{"min":40,"max":60,"offset":1,"def":40,"type":"numeric"},
"decays":{"min":0.00,"max":1.00,"offset":0.05,"def":0.50,"type":"numeric"},
"speeds":{"min":0.0,"max":1.0,"offset":0.1,"def":0.0,"type":"numeric"},
"depths":{"min":0.0,"max":10.0,"offset":0.1,"def":2.0,"type":"numeric"},
},
"filter":"audio"
},
}