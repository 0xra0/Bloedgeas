"""Source tree of the 'dlcvampsword' DLC that adds the Bloedgeas steel sword as a new item.

  python3 -I mk_dlc.py <work dir>     (e.g. ../dlc_src)
Writes <work dir>/pack/dlc/dlcvampsword/... (the files that go into blob0.bundle) and
<work dir>/content/ (w3strings + info.json next to the bundle).

- dlcvampsword.reddlc: Ard Bombs' cooked CDLCDefinition rebuilt (cr2wbuild.py) with our id, keys and
  two mounters, CR4DefinitionsDLCMounter + its NG+ twin, both on data\\gameplay\\items\\.
- The item reuses the vanilla entity template dwarven_sword_lvl1 (the mesh modVampSword replaces) and its
  scabbard scabbard_steel_3_02, so no new w2ent is needed.
- Stats: steel sword level = ceil(1 + (SlashingDamage - 25) / 8), minus 1 for quality 4 (relic), so
  369 is the most a level-43 Geralt can equip; the extra punch is attack_power and crits instead.
  modGearLevelScaling, if enabled for swords, rescales the item to Geralt's level later on.
- Bleed on humans, regeneration and rune FX are script-side (modVampSword/content/scripts/local/bloedgeas.ws);
  the abilities defined here only carry their numbers.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/mnt/ssd/Codex/2026-10-12/i-x20/witcher3-romance-mod/tools")
import w3strings
import icon_texcache
from cr2wbuild import Cr2w

DLC = "dlcvampsword"
ARD_REDDLC = os.path.join(HERE, "..", "dlc_src", "ref", "dlcardbombs.reddlc")   # cooked, from Ard Bombs blob0.bundle
ID_SPACE = 7319                       # unused by the installed DLCs/mods (checked 2026-10-21)
ICON = "icons/inventory/weapons/bloedgeas_64x128.png"

STRINGS = [  # key, {lang: text}   (ids are 2110000000 + ID_SPACE*1000 + row)
    ("item_name_bloedgeas", {"en": "Bloedgeas", "ua": "Блоедгеас"}),
    ("item_desc_bloedgeas", {
        "en": "\"Bloedgeas\" – blood-oath, in the Elder Speech. Dwarven steel from the Mahakam deeps, bought by a "
              "blood-priest of the Coram Agh Tera and consecrated to the Unseen Elder over thirteen nights and "
              "thirteen sacrifices. The runes along the fuller drink whatever the blade spills, and what they drink, "
              "they give back to the hand that holds them.<br><br>"
              "<font color=\"#c0392b\">Against humans: high chance to open wounds that bleed far faster than a common cut.</font><br>"
              "<font color=\"#c0392b\">Blood-oath: while drawn in combat the blade feeds its wielder – slowly while hale, "
              "fiercely when death is near.</font><br>"
              "Not silvered: it holds no terror for monsters.",
        "ua": "«Блоедгеас» – кровна клятва Старшою Мовою. Краснолюдська сталь із глибин Магакаму, яку купив "
              "жрець крові Корам Аг Тера й тринадцять ночей, принісши тринадцять жертв, присвячував Незримому Старійшині. "
              "Руни вздовж долу п'ють усе, що проливає клинок, а випите повертають руці, що його тримає.<br><br>"
              "<font color=\"#c0392b\">Проти людей: висока ймовірність завдати ран, які кровоточать значно швидше за звичайний поріз.</font><br>"
              "<font color=\"#c0392b\">Кровна клятва: коли меч оголено в бою, клинок живить свого власника – повільно, поки той "
              "при силі, і несамовито, коли смерть поруч.</font><br>"
              "Не посріблений: чудовиськ він не лякає."}),
    (DLC, {"en": "Bloedgeas", "ua": "Блоедгеас"}),
    (DLC + "_desc", {"en": "The Bloedgeas steel sword.", "ua": "Сталевий меч Блоедгеас."}),
]
LANGS = ["en", "ua"]   # the game falls back to nothing for other languages: add them here when translated

ITEM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<redxml>
<definitions>
	<abilities>
		<ability name="Bloedgeas _Stats">
			<weight							type="base"	min="4.9"				/>
			<quality						type="add"	min="4"		max="4"		/>
			<SlashingDamage 				type="base"	min="369"				/>
			<SilverDamage 					type="base"	min="1"					/>
			<attack_power					type="mult"	min="0.10"				/>
			<critical_hit_chance			type="add"	min="0.10"				/>
			<critical_hit_damage_bonus		type="add"	min="0.60"				/>
			<desc_bleedingchance_mult		type="add"	min="0.35"				/>
			<human_exp_bonus_when_fatal		type="add"	min="0.05"				/>
		</ability>

		<!-- Numbers for the script-side bleed (bloedgeas.ws applies EET_Bleeding with this as its
		     custom ability, to humans only). Vanilla BleedingEffect is 0.8% max HP/s for 10 s. -->
		<ability name="BloedgeasBleedEffect">
			<DirectDamage					type="mult"	min="0.016"	max="0.016"	/>
			<duration						type="add"	min="8"		max="8"		/>
			<hp_regen_reduction_strength	type="add"	min="200"				/>
			<hp_regen_reduction_duration	type="add"	min="5"					/>
		</ability>
	</abilities>

	<items>
	<item
		name							="Bloedgeas"
		category						="steelsword"
		price							="1450"
		initial_durability				="100"
		max_durability					="100"
		enhancement_slots				="3"
		stackable						="1"
		grid_size						="2"
		equip_template					="dwarven_sword_lvl1"
		equip_slot						="steel_sword_back_slot"
		hold_slot						="r_weapon"
		weapon							="true"
		lethal							="true"
		ability_mode					="OnHold"
		hand							="right"
		sound_identification			="long steel"
		draw_event						="DrawWeapon"
		draw_act						="draw_steel_sword_back_act"
		draw_deact						="draw_steel_sword_back_deact"
		holster_event					="HolsterWeapon"
		holster_act						="holster_steel_sword_back_act"
		holster_deact					="holster_steel_sword_back_deact"
		localisation_key_name			="item_name_bloedgeas"
		localisation_key_description	="item_desc_bloedgeas"
		icon_path						="%(icon)s"
	>
		<tags>							Bloedgeas, PlayerSteelWeapon, Weapon, sword1h, 1handedWeapon, mod_weapon, mod_origin_nonhuman, NoDrop
		</tags>
		<base_abilities>				<a>Default weapon _Stats</a>
										<a>Bloedgeas _Stats</a>
		</base_abilities>
		<recycling_parts>				<parts count="2">Dark steel ingot</parts>
										<parts count="1">Ruby dust</parts>
										<parts count="2">Leather squares</parts>
		</recycling_parts>
		<anim_actions>
										<action name="draw" event="DrawWeapon" act="draw_steel_sword_back_act" deact="draw_steel_sword_back_deact"></action>
										<action name="holster" event="HolsterWeapon" act="holster_steel_sword_back_act" deact="holster_steel_sword_back_deact"></action>
										<action name="attack" event="attack_steel_sword_back" act="attack_steel_sword_back_act" deact="attack_steel_sword_back_deact"></action>
		</anim_actions>
		<anim_switches>
										<anim_switch category="silversword" equip_slot="silver_sword_back_slot" event="silver_to_steel" switch_act="silver_to_steel_act" switch_deact="silver_to_steel_deact"></anim_switch>
		</anim_switches>
		<player_override><bound_items>	<item>scabbard_steel_3_02</item>
		</bound_items></player_override>
	</item>
	</items>
</definitions>
</redxml>
"""


def w2str(s):
    b = s.encode("ascii"); n = len(b)
    return (bytes([0x80 | n]) if n < 64 else bytes([0xC0 | (n & 63), n >> 6])) + b


def reddlc():
    f = Cr2w(open(ARD_REDDLC, "rb").read())
    f.names[f.names.index("dlc_056_710")] = DLC          # the id CName; its hash is regenerated below
    from rigbones import fnv1a32
    f.hashes = [fnv1a32(n.encode("latin-1")) for n in f.names]
    ix = f.name
    prop = lambda n, t, v: struct.pack("<HHI", ix(n), ix(t), 4 + len(v)) + v
    ptrs = [2, 3]
    definition = (b"\0" + prop("id", "CName", struct.pack("<H", ix(DLC)))
                  + prop("localizedNameKey", "String", w2str(DLC))
                  + prop("localizedDescriptionKey", "String", w2str(DLC + "_desc"))
                  + prop("mounters", "array:2,0,ptr:IGameplayDLCMounter", struct.pack("<I", len(ptrs)) + b"".join(struct.pack("<I", p) for p in ptrs))
                  + prop("visibleInDLCMenu", "Bool", b"\0") + prop("requiredByGameSave", "Bool", b"\0") + b"\0\0")
    items_dir = "dlc\\%s\\data\\gameplay\\items\\" % DLC
    mounter = b"\0" + prop("definitionXmlFilePath", "String", w2str(items_dir)) + b"\0\0"
    old = f.exports
    f.exports = [[old[0][0], old[0][1], 0, definition, None],
                 [ix("CR4DefinitionsDLCMounter"), old[1][1], 1, mounter, None],
                 [ix("CR4DefinitionsNGPlusDLCMounter"), old[1][1], 1, mounter, None]]
    return f.bytes()


def main(work):
    pack = os.path.join(work, "pack", "dlc", DLC)
    content = os.path.join(work, "content")
    for d in (pack + "/data/gameplay/items", content):
        os.makedirs(d, exist_ok=True)
    open(f"{pack}/{DLC}.reddlc", "wb").write(reddlc())
    open(f"{pack}/data/gameplay/items/def_item_bloedgeas.xml", "w", encoding="utf-8-sig", newline="\r\n").write(ITEM_XML.replace("%(icon)s", ICON))
    # the GUI looks icons up in the texture caches by depot path, so the icon ships cooked next to the bundle
    # under the DLC's own gui_new and under vanilla's, since which root the GUI resolves a DLC icon from is unproven
    icon = ICON.replace("/", "\\")
    icon_texcache.main(os.path.join(work, "bloedgeas_64x128.png"), f"{content}/texture.cache",
                       "dlc\\%s\\data\\gameplay\\gui_new\\%s" % (DLC, icon), "gameplay\\gui_new\\" + icon)
    for lang in LANGS:
        rows = [(2110000000 + ID_SPACE * 1000 + i, k, t[lang]) for i, (k, t) in enumerate(STRINGS)]
        km = w3strings.LANGS.get(lang, (0, 0))
        w3strings.write(f"{content}/{lang}.w3strings", lang, rows, key_magic=km)
    json.dump({"name": DLC, "modName": "Bloedgeas", "version": "1.0", "gameVersion": "29",
               "description": "Bloedgeas, a blood-oath steel sword", "author": "home", "idSpace": ID_SPACE,
               "workshopId": 0, "succesfullyCooked": True, "dependencies": [], "useLooseScripts": True},
              open(f"{content}/info.json", "w"), indent=4)
    print("dlc tree ->", work)


if __name__ == "__main__":
    main(sys.argv[1])
