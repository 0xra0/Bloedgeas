// Bloedgeas, the blood-oath sword (item 'Bloedgeas' from the dlcvampsword DLC, tag 'Bloedgeas').
//  - melee hits on humans: chance to open a heavy bleed (ability BloedgeasBleedEffect) + rune flare + life-leech beam
//  - killing blows: blood burst on the body
//  - while drawn in combat: Geralt regenerates a share of max HP per second, more when near death
//  - near death the runes keep burning (looped runeword_igni: glow, light and its own sound) and a heartbeat loops
// The FX names are effects of sword_steel_fx.w2ent, which every witcher sword template includes;
// their tracks carry the dynamic lights and the sound events.

function Bloedgeas_BleedChance() : float		{ return 0.35; }
function Bloedgeas_CriticalHP() : float			{ return 0.30; }
function Bloedgeas_FlareCooldown() : float		{ return 2.5; }
function Bloedgeas_SoundBank() : string			{ return "bloedgeas.bnk"; }	// in dlc/dlcvampsword/content/soundspc.cache
// Vanilla FX entities, spawned where needed: the Caretaker's life-drain beam and the blood burst Ciri's dash uses.
function Bloedgeas_LeechFX() : string			{ return "dlc\ep1\data\fx\characters\caretaker\drain_life.w2ent"; }
function Bloedgeas_BurstFX() : string			{ return "fx\blood\explode\blood_explode.w2ent"; }

// Fraction of max vitality restored per second while Bloedgeas is drawn in combat.
// hpPercent is Geralt's current vitality, 0..1.
function Bloedgeas_RegenRate(hpPercent : float) : float
{
	// TODO(you): shape the blood-oath curve. Placeholder: flat 0.4%/s.
	return 0.004;
}

@addField(CR4Player) var bloedgeasGlowSword : CEntity;
@addField(CR4Player) var bloedgeasLastFlare : float;

function Bloedgeas_HeldSword(p : W3PlayerWitcher) : CWitcherSword
{
	var id : SItemUniqueId;

	if (!p)
		return NULL;
	id = p.GetHeldSword();
	if (!p.inv.IsIdValid(id) || !p.inv.ItemHasTag(id, 'Bloedgeas'))
		return NULL;
	return p.GetHeldSwordEntity();
}

function Bloedgeas_Bleed(attacker : CR4Player, victim : CActor)
{
	var params : SCustomEffectParams;

	params.effectType = EET_Bleeding;
	params.creator = attacker;
	params.sourceName = "Bloedgeas";
	params.customAbilityName = 'BloedgeasBleedEffect';
	params.duration = 8;
	victim.AddEffectCustom(params);
}

// Torso FX slot of an actor, or the actor itself when its template has none (as btTaskCaretakerManager does).
function Bloedgeas_Torso(a : CActor) : CNode
{
	var n : CNode;

	n = a.GetComponent("torso3effect");
	if (!n)
		n = a;
	return n;
}

// Life-leech beam from the victim's chest to Geralt's. The template's 'drain_energy' effect stretches its
// particles towards the target node it is given and brings its own drain sound.
function Bloedgeas_Leech(attacker : CActor, victim : CActor)
{
	var fx : CEntity;

	fx = theGame.CreateEntity((CEntityTemplate)LoadResource(Bloedgeas_LeechFX(), true),
		Bloedgeas_Torso(victim).GetWorldPosition(), victim.GetWorldRotation());
	if (!fx)
		return;
	fx.PlayEffect('drain_energy', Bloedgeas_Torso(attacker));
	fx.DestroyAfter(1.5);
}

// Blood burst on the body of whatever the killing blow felled.
function Bloedgeas_Burst(victim : CActor)
{
	var fx : CEntity;
	var pos : Vector;

	pos = victim.GetWorldPosition();
	pos.Z += 0.7;
	fx = theGame.CreateEntity((CEntityTemplate)LoadResource(Bloedgeas_BurstFX(), true), pos);
	if (!fx)
		return;
	fx.PlayEffect('blood_explode');
	fx.DestroyAfter(5.0);
}

// The hit path. The processor calls this on the attacker after the damage is resolved, only when the
// victim was alive (damageManagerProcessor.ws:145); modSwordFXRemaster wraps the same event.
@wrapMethod(W3PlayerWitcher) function OnProcessActionPost(action : W3DamageAction)
{
	var attack : W3Action_Attack;
	var victim : CActor;
	var sword : CWitcherSword;
	var now : float;
	var res : bool;

	res = wrappedMethod(action);		// an event: it returns bool, so every return passes this on
	attack = (W3Action_Attack)action;
	if (!attack || !attack.IsActionMelee())
		return res;
	if (!action.DealtDamage() || action.IsDoTDamage())
		return res;
	if (action.WasDodged() || attack.IsParried() || attack.IsCountered())
		return res;
	if (!inv.ItemHasTag(attack.GetWeaponId(), 'Bloedgeas'))
		return res;

	sword = (CWitcherSword)inv.GetItemEntityUnsafe(attack.GetWeaponId());
	if (sword)
		sword.PlayEffectSingle('fast_attack_buff_hit');		// every landed hit: short hum + light pulse
	theSound.SoundEvent("Play_bloedgeas_hit");				// our own Wwise bank: random of 3 variants (audio/src/bloedgeas_hit*.wav), 2D

	victim = (CActor)action.victim;
	if (!victim)
		return res;
	if (!victim.IsAlive())
	{
		Bloedgeas_Burst(victim);		// the killing blow: no bleed on a corpse
		return res;
	}
	if (!victim.IsHuman() || RandF() >= Bloedgeas_BleedChance())
		return res;

	Bloedgeas_Bleed(this, victim);

	now = theGame.GetEngineTimeAsSeconds();
	if (sword && now - bloedgeasLastFlare >= Bloedgeas_FlareCooldown())
	{
		bloedgeasLastFlare = now;
		sword.PlayEffectSingle('igni_power');				// rune flare: fire glow, light, 4 sound hits
		sword.PlayEffectSingle('strong_attack_buff_hit');
		theSound.SoundEvent("Play_bloedgeas_bleed");		// blood sting, 2 random variants; on the flare cooldown so a combo doesn't stack it
		Bloedgeas_Leech(this, victim);
	}
	return res;
}

// Keep existing Bloedgeas copies at the wielder's level without depending on the general gear menu.
function Bloedgeas_ScaleInventory(p : W3PlayerWitcher)
{
	var inventory : CInventoryComponent;
	var swords : array<SItemUniqueId>;
	var settings : SGLSSettings;
	var i : int;

	if (!p)
		return;
	inventory = p.GetInventory();
	if (!inventory)
		return;

	settings.valid = true;
	settings.enabled = true;
	settings.swords = true;
	swords = inventory.GetItemsByName('Bloedgeas');
	for (i = 0; i < swords.Size(); i += 1)
		GLS_ScaleItem(p, inventory, swords[i], settings);
}

@addMethod(CR4Player) timer function Bloedgeas_Tick(dt : float, id : int)
{
	var sword : CWitcherSword;
	var hp : float;
	var critical : bool;

	Bloedgeas_ScaleInventory((W3PlayerWitcher)this);

	sword = Bloedgeas_HeldSword((W3PlayerWitcher)this);
	critical = false;
	if (sword && IsAlive() && IsInCombat())
	{
		hp = GetStatPercents(BCS_Vitality);
		if (hp < 1)
			GainStat(BCS_Vitality, Bloedgeas_RegenRate(hp) * GetStatMax(BCS_Vitality) * dt);
		critical = hp < Bloedgeas_CriticalHP();
	}

	if (critical && bloedgeasGlowSword != sword)
	{
		Bloedgeas_StopGlow(this);
		sword.PlayEffect('runeword_igni');
		sword.PlayEffect('weapon_blood_stage2');
		theSound.SoundEvent("Play_bloedgeas_heartbeat");	// loops in Wwise until Stop_bloedgeas_heartbeat
		bloedgeasGlowSword = sword;
	}
	else if (!critical && bloedgeasGlowSword)
	{
		Bloedgeas_StopGlow(this);
	}
}

function Bloedgeas_StopGlow(p : CR4Player)
{
	if (p.bloedgeasGlowSword)
	{
		p.bloedgeasGlowSword.StopEffect('runeword_igni');
		p.bloedgeasGlowSword.StopEffect('weapon_blood_stage2');
		theSound.SoundEvent("Stop_bloedgeas_heartbeat");
	}
	p.bloedgeasGlowSword = NULL;
}

@wrapMethod(CR4Player) function OnSpawned(spawnData : SEntitySpawnData)
{
	wrappedMethod(spawnData);
	if (!theSound.SoundIsBankLoaded(Bloedgeas_SoundBank()))
		theSound.SoundLoadBank(Bloedgeas_SoundBank(), true);
	AddTimer('Bloedgeas_Tick', 0.5, true);
}

// Vanilla tooltips leave the description empty for every weapon and armour (guiTooltipComponent.ws,
// GetBaseItemData: only Aerondight & co. are special-cased), so put ours back. modShopOwnedCount wraps
// the same function and appends to "Description"; wraps chain, so both lines survive.
@wrapMethod(W3TooltipComponent)
function GetBaseItemData( item : SItemUniqueId, itemInvComponent : CInventoryComponent, optional isShopItem : bool, optional compareWithItem : SItemUniqueId, optional compareItemInv : CInventoryComponent ) : CScriptedFlashObject
{
	var data : CScriptedFlashObject;
	var desc, rest : string;

	data = wrappedMethod( item, itemInvComponent, isShopItem, compareWithItem, compareItemInv );
	if ( !data || !itemInvComponent.ItemHasTag( item, 'Bloedgeas' ) )
		return data;
	desc = GetLocStringByKeyExt( itemInvComponent.GetItemLocalizedDescriptionByUniqueID( item ) );
	rest = data.GetMemberFlashString( "Description" );		// empty from vanilla; another mod's line if it wrapped first
	if ( rest != "" )
		desc += "<br>" + rest;
	data.SetMemberFlashString( "Description", desc );
	return data;
}
