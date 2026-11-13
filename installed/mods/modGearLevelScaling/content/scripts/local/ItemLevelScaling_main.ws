struct SGLSSettings
{
    var valid, enabled, downscale, swords, armor : bool;
    var scope : int;
    var key : string;
}

function GLS_ReadSettings() : SGLSSettings
{
    var c : CInGameConfigWrapper;
    var s : SGLSSettings;
    var a, b, d, e, f : string;

    c = theGame.GetInGameConfigWrapper();

    if (!c)
        return s;

    a = c.GetVarValue('ILS_Config', 'ILS_Enable');
    b = c.GetVarValue('ILS_Config', 'ILS_Downscale');
    d = c.GetVarValue('ILS_Config', 'ILS_Swords');
    e = c.GetVarValue('ILS_Config', 'ILS_Armor');
    f = c.GetVarValue('ILS_Config', 'ILS_Scope');

    s.enabled   = (bool)a;
    s.downscale = (bool)b;
    s.swords    = (bool)d;
    s.armor     = (bool)e;
    s.scope     = (int)f;

    s.key = a + ":" + b + ":" + d + ":" + e + ":" + f;
    s.valid = s.scope >= 0 && s.scope <= 3;

    return s;
}

function GLS_Kind(
    inv : CInventoryComponent,
    item : SItemUniqueId
) : name
{
    var c : name;

    c = inv.GetItemCategory(item);

    if (c == 'steelsword' && inv.ItemHasTag(item, 'PlayerSteelWeapon'))
        return 'steel';

    if (c == 'silversword' && inv.ItemHasTag(item, 'PlayerSilverWeapon'))
        return 'silver';

    if (c == 'armor')
        return 'armor';

    if (c == 'gloves')
        return 'gloves';

    if (c == 'pants' || c == 'boots')
        return 'pants';

    return 'None';
}

function GLS_Ability(k : name) : name
{
    if (k == 'steel')
        return 'autogen_fixed_steel_dmg';

    if (k == 'silver')
        return 'autogen_fixed_silver_dmg';

    if (k == 'armor')
        return 'autogen_fixed_armor_armor';

    if (k == 'gloves')
        return 'autogen_fixed_gloves_armor';

    if (k == 'pants')
        return 'autogen_fixed_pants_armor';

    return 'None';
}

function GLS_CountAbility(
    inv : CInventoryComponent,
    item : SItemUniqueId,
    a : name
) : int
{
    var x : array<name>;
    var i, n : int;

    inv.GetItemContainedAbilities(item, x);

    for (i = 0; i < x.Size(); i += 1)
    {
        if (x[i] == a)
            n += 1;
    }

    return n;
}

// Positive amount adds abilities; negative amount removes them.
function GLS_ApplyCount(
    inv : CInventoryComponent,
    item : SItemUniqueId,
    a : name,
    amount : int
) : bool
{
    var before, i : int;

    if (amount == 0)
        return true;

    if (amount < -256 || amount > 256)
        return false;

    before = GLS_CountAbility(inv, item, a);

    if (amount < 0 && before < -amount)
        return false;

    if (amount > 0)
    {
        for (i = 0; i < amount; i += 1)
            inv.AddItemCraftedAbility(item, a, true);
    }
    else
    {
        for (i = 0; i < -amount; i += 1)
            inv.RemoveItemCraftedAbility(item, a);
    }

    // Attribute caches update after this script call,
    // so do not validate here.
    return true;
}

// Mirrors GetItemLevel without its level-100 cap.
function GLS_UncappedLevel(
    inv : CInventoryComponent,
    item : SItemUniqueId,
    k : name
) : int
{
    var names : array<name>;
    var v : SAbilityAttributeValue;
    var sum : float;
    var i, l, q : int;

    if (k == 'steel' || k == 'silver')
    {
        if (k == 'steel')
            names.PushBack('SlashingDamage');
        else
            names.PushBack('SilverDamage');

        names.PushBack('BludgeoningDamage');
        names.PushBack('RendingDamage');
        names.PushBack('ElementalDamage');
        names.PushBack('FireDamage');
        names.PushBack('PiercingDamage');

        if (k == 'steel')
            names.PushBack('SilverDamage');

        for (i = 0; i < names.Size(); i += 1)
        {
            v = inv.GetItemAttributeValue(item, names[i]);
            sum += v.valueBase - 1;
        }

        if (k == 'steel')
            l = CeilF((1 + sum - 25) / 8);
        else
            l = CeilF((1 + sum - 90) / 10);
    }
    else
    {
        v = inv.GetItemAttributeValue(item, 'armor');

        if (k == 'armor')
            l = FloorF((v.valueBase - 25) / 5);
        else if (k == 'gloves')
            l = FloorF((v.valueBase - 1) / 2);
        else
            l = FloorF((v.valueBase - 5) / 2);
    }

    q = inv.GetItemQuality(item);

    if (q == 5)
        l -= 2;
    else if (q == 4)
        l -= 1;

    if (l < 1)
        l = 1;

    if (inv.ItemHasTag(item, 'OlgierdSabre'))
        l -= 3;

    if ((q == 4 || q == 5) && inv.ItemHasTag(item, 'EP1'))
        l -= 1;

    return l;
}

function GLS_InScope(
    p : W3PlayerWitcher,
    inv : CInventoryComponent,
    item : SItemUniqueId,
    k : name,
    s : SGLSSettings
) : bool
{
    // Bloedgeas grows with its wielder independently of the general gear options.
    if (inv.ItemHasTag(item, 'Bloedgeas'))
        return true;

    if (!s.enabled || !s.valid || inv.ItemHasTag(item, 'Aerondight'))
        return false;

    if ((k == 'steel' || k == 'silver') && !s.swords)
        return false;

    if (k != 'steel' && k != 'silver' && !s.armor)
        return false;

    if (s.scope == 1 && !p.IsItemEquipped(item))
        return false;

    if (s.scope == 2 && inv.GetItemQuality(item) != 5)
        return false;

    if (s.scope == 3 && !inv.ItemHasTag(item, 'scalable'))
        return false;

    return true;
}

function GLS_BaseLevel(
    inv : CInventoryComponent,
    item : SItemUniqueId,
    k : name
) : int
{
    var base, tracked : int;

    tracked = inv.GetItemModifierInt(item, 'GLS2_delta', 0);

    if (inv.GetItemModifierInt(item, 'GLS2_initialized', 0) > 0)
        return inv.GetItemModifierInt(item, 'GLS2_baseLevel', 1);

    // Subtraction also migrates saves made with the first v2 build.
    base = GLS_UncappedLevel(inv, item, k) - tracked;

    inv.SetItemModifierInt(item, 'GLS2_baseLevel', base);
    inv.SetItemModifierInt(item, 'GLS2_initialized', 1);

    return base;
}

// Computes the entire level difference before modifying the item.
// The game refreshes item attributes after this script call,
// not after every ability.
function GLS_ScaleItem(
    p : W3PlayerWitcher,
    inv : CInventoryComponent,
    item : SItemUniqueId,
    s : SGLSSettings
) : int
{
    var k, a : name;
    var old, desired, change, base, target : int;

    if (!inv.IsIdValid(item))
        return 1;

    k = GLS_Kind(inv, item);

    if (k == 'None')
        return 1;

    a = GLS_Ability(k);

    old = inv.GetItemModifierInt(item, 'GLS2_delta', 0);
    base = GLS_BaseLevel(inv, item, k);

    if (GLS_InScope(p, inv, item, k, s))
    {
        target = Clamp(p.GetLevel(), 1, p.GetMaxLevel());

        if (base < target)
            desired = target - base;
        else if (base > target && s.downscale)
            desired = target - base;
    }

    change = desired - old;

    if (!GLS_ApplyCount(inv, item, a, change))
        return 2;

    inv.SetItemModifierInt(item, 'GLS2_delta', desired);

    return 0;
}

function GLS_ScaleItems(
    items : array<SItemUniqueId>,
    s : SGLSSettings
)
{
    var p : W3PlayerWitcher;
    var inv : CInventoryComponent;
    var i, failed : int;

    p = GetWitcherPlayer();

    if (!p || !p.GLS_IsReady() || !s.valid)
        return;

    inv = p.GetInventory();

    if (!inv)
        return;

    for (i = 0; i < items.Size(); i += 1)
    {
        if (GLS_ScaleItem(p, inv, items[i], s) == 2)
            failed += 1;
    }

    if (failed > 0)
    {
        LogChannel(
            'ILS',
            "GLS2: unable to safely scale " + failed + " item(s)."
        );
    }
}

function GLS_ScaleInventory(s : SGLSSettings)
{
    var p : W3PlayerWitcher;
    var inv : CInventoryComponent;
    var items : array<SItemUniqueId>;

    p = GetWitcherPlayer();

    if (!p || !p.GLS_IsReady())
        return;

    inv = p.GetInventory();

    if (!inv)
        return;

    inv.GetAllItems(items);
    GLS_ScaleItems(items, s);
}

function GLS_OnItemsAdded(items : array<SItemUniqueId>)
{
    GLS_ScaleItems(items, GLS_ReadSettings());
}

function GLS_OnEquipmentChanged(item : SItemUniqueId)
{
    var items : array<SItemUniqueId>;

    items.PushBack(item);
    GLS_ScaleItems(items, GLS_ReadSettings());
}