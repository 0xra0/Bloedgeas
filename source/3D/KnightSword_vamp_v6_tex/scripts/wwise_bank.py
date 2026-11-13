"""Build bloedgeas.bnk from audio/src/*.wav through WAAPI over HTTP (no Python deps).

  /mnt/sata/wwise/wc.sh waapi-server 'C:\\wwproj\\bloedgeas\\bloedgeas.wproj' --http-port 8097 --wamp-port 8098 &
  python3 -I wwise_bank.py <out dir>          (e.g. ../audio/build)

- The project C:\\wwproj\\bloedgeas is a tiny standalone one, not REDkit's 29 GB w3_audio. That works because
  Wwise gives busses (like events and banks) ShortIDs hashed from their NAME: our bus "Combat_weapon" has the
  same id as the game's, so the sounds route into the game's real mixer (and its volume sliders) via Init.bnk.
  Never ship our own Init.bnk.
- Every SOUNDS row becomes a Random Container "<name>_rnd" holding one Sound SFX per variant wav, + an event
  "Play_<name>" (and "Stop_<name>" for a loop) in one bank, media embedded in the bank (not streamed), so the cache holds only bloedgeas.bnk.
  The container picks a variant at random and never the same one twice in a row, so repeated hits differ.
- "pitch": (min, max) cents is a Wwise randomizer on the container: each play gets its own pitch in that range,
  so even the same variant never sounds twice alike. "loop": the sounds repeat until Stop_<name> is posted.
"""
import json, os, struct, sys, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "audio", "src")
URL = "http://127.0.0.1:8097/waapi"
BANK = "bloedgeas"
W3_PROJECT_ID = 39            # BKHD project id of the vanilla banks
BUS = "Combat_weapon"          # a W3 bus (Master Audio Bus > Gameplay Master Bus > Combat > Combat_weapon)
PROJ_HOST = "/mnt/sata/wwise/prefix/drive_c/wwproj/bloedgeas"
AMH = "\\Actor-Mixer Hierarchy\\Default Work Unit"

SOUNDS = [  # event stem, volume dB, variant wav stems, options
    # +6 dB: at 0 it was masked by the vanilla hit sounds. SoundCraft v3 recipe (katakan bite + blood squirt +
    # silver-sword monster add pitched down, saturated); _b/_c swap in other takes of each layer (-3/-5 st)
    ("bloedgeas_hit", 6, ["bloedgeas_hit", "bloedgeas_hit_b", "bloedgeas_hit_c"], {"pitch": (-150, 100)}),
    # mk_sfx_extra.py: Dettlaff blood-construct swell + squirt, once per opened bleed
    ("bloedgeas_bleed", 4, ["bloedgeas_bleed", "bloedgeas_bleed_b"], {"pitch": (-100, 100)}),
    # mk_sfx_extra.py: 80 bpm lub-dub, seamless; runs while the runes burn near death
    ("bloedgeas_heartbeat", 2, ["bloedgeas_heartbeat"], {"loop": True}),
]


def waapi(uri, args=None, options=None):
    body = json.dumps({"uri": uri, "args": args or {}, "options": options or {}}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        sys.exit(f"{uri}: {e.read().decode(errors='replace')}")


def win(p):
    return "Z:" + os.path.abspath(p).replace("/", "\\")


def main(out):
    print(waapi("ak.wwise.core.getInfo")["displayName"], "connected")
    bus = waapi("ak.wwise.core.object.create", {
        "parent": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus",
        "type": "Bus", "name": BUS, "onNameConflict": "merge"})["id"]

    waapi("ak.wwise.core.audio.import", {
        "importOperation": "replaceExisting",
        "default": {"importLanguage": "SFX"},
        "imports": [{"audioFile": win(os.path.join(SRC, v + ".wav")),
                     "objectPath": f"{AMH}\\<Random Container>{s}_rnd\\<Sound SFX>{v}"}
                    for s, _, variants, _ in SOUNDS for v in variants]})
    for s, vol, variants, opt in SOUNDS:
        path = f"{AMH}\\{s}_rnd"
        props = [("RandomOrSequence", 1),                       # 1 = Random
                 ("NormalOrShuffle", 1),                        # 1 = Standard: any variant but the last one(s)
                 ("RandomAvoidRepeating", len(variants) > 1),   # nothing to avoid with one variant
                 ("Volume", vol)]
        if len(variants) > 1:
            props.append(("RandomAvoidRepeatingCount", 1))
        for prop, value in props:
            waapi("ak.wwise.core.object.setProperty", {"object": path, "property": prop, "value": value})
        lo, hi = opt.get("pitch", (0, 0))
        waapi("ak.wwise.core.object.setRandomizer", {"object": path, "property": "Pitch",
                                                     "enabled": "pitch" in opt, "min": lo, "max": hi})
        for v in variants:                                      # looping is a property of the Sound, not the container
            waapi("ak.wwise.core.object.setProperty", {"object": f"{path}\\{v}", "property": "IsLoopingEnabled",
                                                       "value": bool(opt.get("loop"))})
        waapi("ak.wwise.core.object.setProperty", {"object": path, "property": "OverrideOutput", "value": True})
        waapi("ak.wwise.core.object.setReference", {"object": path, "reference": "OutputBus", "value": bus})
        waapi("ak.wwise.core.object.create", {
            "parent": "\\Events\\Default Work Unit", "type": "Event", "name": "Play_" + s,
            "onNameConflict": "replace",
            "children": [{"name": "", "type": "Action", "@ActionType": 1, "@Target": path}]})     # 1 = Play
        if opt.get("loop"):
            waapi("ak.wwise.core.object.create", {
                "parent": "\\Events\\Default Work Unit", "type": "Event", "name": "Stop_" + s,
                "onNameConflict": "replace",
                "children": [{"name": "", "type": "Action", "@ActionType": 2, "@Target": path}]})  # 2 = Stop

    bank = waapi("ak.wwise.core.object.create", {
        "parent": "\\SoundBanks\\Default Work Unit", "type": "SoundBank", "name": BANK,
        "onNameConflict": "merge"})["id"]
    waapi("ak.wwise.core.soundbank.setInclusions", {
        "soundbank": bank, "operation": "replace",
        "inclusions": [{"object": f"\\Events\\Default Work Unit\\{e}_{s}",
                        "filter": ["events", "structures", "media"]}
                       for s, _, _, opt in SOUNDS for e in (("Play", "Stop") if opt.get("loop") else ("Play",))]})
    waapi("ak.wwise.core.project.save")

    r = waapi("ak.wwise.core.soundbank.generate", {
        "soundbanks": [{"name": BANK}], "platforms": ["Windows"], "writeToDisk": True,
        "rebuildSoundBanks": True, "clearAudioFileCache": False})
    for m in r.get("logs", []):
        if m.get("severity") in ("Error", "Fatal Error", "Warning"):
            print(" ", m.get("severity"), m.get("message"))

    built = os.path.join(PROJ_HOST, "GeneratedSoundBanks", "Windows", BANK + ".bnk")
    os.makedirs(out, exist_ok=True)
    bnk = bytearray(open(built, "rb").read())
    # BKHD: version, bank id, language id, alignment/flags, project id. Ours says 0, every vanilla bank 39;
    # set it to the game's so nothing in the bank manager can reject the bank as foreign.
    assert bnk[:4] == b"BKHD" and struct.unpack_from("<I", bnk, 8)[0] == 150, "not a Wwise 2023.1 (v150) bank"
    struct.pack_into("<I", bnk, 8 + 16, W3_PROJECT_ID)
    dst = os.path.join(out, BANK + ".bnk")
    open(dst, "wb").write(bnk)
    print("bank ->", dst, len(bnk), "bytes")


if __name__ == "__main__":
    main(sys.argv[1])
