# Képnézegető HTML Modul Sablon (V13.8 — Végleges)

Ez a dokumentum a **System Activity** modul véglegesített, pixel-pontos struktúráját írja le, amely az összes többi modul (`laborModule`, `connectionModule`, `categoriesModule`, `musicModule`, `moverModule`) átalakításának alapjául szolgál.

---

## FONTOS: Elhelyezkedés a DOM-ban

Az összes modul (`div.module-page`) a fő `container` dobozon **KÍVÜL** helyezkedik el, közvetlenül a `<body>` szintjén. Emiatt a modulok saját maguk felelnek a teljes oldal belső távolságainak beállításáért.

---

## 1. Modul Gyökérelem (`.module-page`)

Ez az elem alapból el van rejtve (`display: none`), és a navigáció során kap `active` osztályt, ami megjeleníti.

```html
<div id="activityModule" class="module-page w-full flex-col items-center justify-start pb-20 pt-8">
```

| Osztály | Érték | Magyarázat |
|---|---|---|
| `module-page` | CSS osztály | Alapból `display: none`, JS vezérli |
| `w-full` | 100% | Teljes szélességet foglalja el |
| `flex-col` | column | Tartalom fentről lefelé épül |
| `items-center` | center | Minden gyerm elem vízszintesen középre zárt |
| `justify-start` | start | Tartalom felülről indul |
| `pt-8` | 32px | **KRITIKUS!** Egyenlíti ki a főoldal `container` dobozának `py-8` (32px) felső eltolását, hogy a Lumina felirat pixel-pontosan ugyanott jelenjen meg, mint a főoldalon |
| `pb-20` | 80px | Alul lélegzetvételnyi tér, hogy a tartalom ne tapadjon a képernyő aljára |

---

## 2. Fejléc Sáv (Header Bar)

A "topbar": bal oldalon a Lumina brandingge, jobb oldalon a Főoldal gomb. Ez egy önálló, átlátszó sáv — nem kártya, nincs háttere.

```html
<div class="w-full max-w-2xl mx-auto px-6 flex flex-col items-start pt-2 pb-3 sm:pt-3 sm:pb-5">
    <div class="w-full flex items-start justify-between">
        ...
    </div>
</div>
```

| Osztály | Érték | Magyarázat |
|---|---|---|
| `w-full` | 100% | Teljes szélességű sáv |
| `max-w-2xl` | 672px | Maximális szélesség (megegyezik a kártya szélességével!) |
| `mx-auto` | auto | Vízszintesen középre zárva |
| `px-6` | 24px | **KRITIKUS!** Megegyezik a kártya belső padding-jával, így Lumina és a kártya bal széle pontosan egy vonalban van |
| `pt-2 sm:pt-3` | 8px / 12px | Felső belső tér a sávban (mobilon kisebb) |
| `pb-3 sm:pb-5` | 12px / 20px | Alsó belső tér (a sáv és a kártya között) |
| `flex items-start justify-between` | — | A sáv belseje: LuminaBranding balra, Főoldal gomb jobbra, mindkettő a tetejéhez igazítva |

### 2.1. Lumina Branding (bal oldal)

```html
<div class="flex items-start">
    <span class="text-3xl sm:text-4xl font-black text-transparent bg-clip-text
                 bg-gradient-to-r from-indigo-500 to-purple-600 tracking-tighter
                 drop-shadow-sm select-none leading-none">Lumina</span>
</div>
```

- **Betűméret:** `text-3xl` (30px) mobilon, `sm:text-4xl` (36px) tablettől
- **Vastagság:** `font-black` (900-as súlyú betű)
- **Szín:** Átmenetes, `from-indigo-500 to-purple-600` (kék-lila gradiens)
- **`leading-none`:** Nulla sorköz — biztosítja, hogy a Lumina szöveg "teteje" precízen illeszkedjen a fejléc tetejéhez
- **`select-none`:** A szöveg nem jelölhető ki (logószerű viselkedés)

### 2.2. Főoldal Gomb (jobb oldal)

```html
<button onclick="showMainMenu()"
        class="flex flex-col items-center gap-1 group transition-all hover:scale-105 active:scale-95 no-underline">
    <div class="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-indigo-100 text-indigo-600
                flex items-center justify-center
                group-hover:bg-indigo-600 group-hover:text-white
                transition-all shadow-sm border border-indigo-200/50 backdrop-blur-md">
        <i data-lucide="home" class="w-6 h-6 sm:w-7 sm:h-7"></i>
    </div>
    <span class="text-[10px] sm:text-[11px] font-black text-indigo-400
                 group-hover:text-indigo-600 uppercase tracking-widest transition-colors">Főoldal</span>
</button>
```

| Tulajdonság | Érték | Megjegyzés |
|---|---|---|
| Gomb forma | `flex-col`, ikon felül, felirat alul | Mindkét modulon azonos |
| Mobilos ikontér | `w-12 h-12` (48×48px) | |
| Tablet ikontér | `sm:w-14 sm:h-14` (56×56px) | |
| Lekerekítés | `rounded-2xl` | |
| Alap háttér | `bg-indigo-100` (világos kék) | |
| Hover háttér | `group-hover:bg-indigo-600` (telített kék) | |
| Felirat | `Főoldal`, 10-11px, `uppercase`, `font-black` | |
| Animáció | `hover:scale-105`, `active:scale-95` | Mikro-animáció kattintáskor |

---

## 3. Tartalom konténer

A fejléc és a kártya(ák) közötti összefoglaló elem.

```html
<div class="space-y-8 w-full max-w-[500px] md:max-w-2xl mx-auto px-4 sm:px-6">
```

| Osztály | Értéke | Magyarázat |
|---|---|---|
| `space-y-8` | 32px | Kártyák közötti függőleges rés (ha több is van) |
| `w-full` | 100% | **KÖTELEZŐ!** Nélküle asztali nézetben balra csúszik a tartalom |
| `max-w-[500px]` | 500px | Mobilos maximális szélesség |
| `md:max-w-2xl` | 672px | Tablet és desktop maximális szélesség |
| `mx-auto` | auto | Középre zárva |
| `px-4 sm:px-6` | 16px / 24px | Oldalsó belső margók |

---

## 4. Tartalom Kártya (Glass Panel)

A tényleges "munkaterület". Ez egy lebegő üveg-hatású doboz.

```html
<div class="glass-panel w-full rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
    <div class="relative z-10">
        ...
    </div>
</div>
```

| Osztály | Értéke | Magyarázat |
|---|---|---|
| `glass-panel` | CSS osztály | Áttetsző fehér üveghatás (a CSS-ben definiálva) |
| `w-full` | 100% | Tölti ki a 3. pont konténerét |
| `rounded-3xl` | 24px lekerekítés | Erősen lekerekített sarkok |
| `p-6 sm:p-8` | 24px / 32px | Belső padding (mobilon kisebb) |
| `shadow-2xl` | — | Mély árnyék, "lebegő" hatáshoz |
| `relative overflow-hidden` | — | A belső dekorációs elemek ne lógjanak ki |
| `relative z-10` | — | Belső tartalom a dekorációk felett marad |

### 4.1. Kártya fejléce (Title Bar a kártyán belül)

A kártya első eleme mindig egy belső fejléc szekció, elválasztó vonallal.

```html
<div class="w-full flex flex-col sm:flex-row justify-between items-start sm:items-center
            pb-6 sm:pb-8 border-b border-indigo-50 mb-8 border-opacity-50 gap-4">

    <!-- Bal oldal: Cím + Alcím -->
    <div class="flex flex-col items-start">
        <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-slate-800 flex items-center gap-2">
            <i data-lucide="activity" class="text-indigo-500 w-6 h-6"></i>
            System Activity
            <span class="text-[10px] text-indigo-400 font-black ml-1">V13.8</span>
        </h1>
        <p class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1 ml-8">
            Rendszer állapot és kapcsolatok
        </p>
    </div>

    <!-- Jobb oldal: Státusz kijelző / Badge -->
    <div class="flex items-center gap-2 bg-indigo-50 px-3 py-1.5 rounded-full border border-indigo-100 shadow-inner">
        <div class="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></div>
        <span class="text-indigo-600 font-black text-sm" id="activeClientsCount">0</span>
        <span class="text-[10px] text-indigo-400 font-bold uppercase tracking-widest">Active Clients</span>
    </div>

</div>
```

**Fontos szabályok:**
- Mobilon (`flex-col`): cím felül, badge alul, bal élre igazítva
- Tablettől (`sm:flex-row`): cím bal oldalt, badge jobb oldalt, alap-vonalra igazítva
- Alcím szöveg mindig `ml-8` (32px balra tolás) hogy az ikon alatt ne kezdődjön
- Elválasztó vonal: `border-b border-indigo-50 border-opacity-50` — diszkrét, halvány
- Alul `mb-8` (32px) a tartalom és az elválasztó közt

---

## 5. Tartalom elemek a kártyán belül

A kártya fejléce után jönnek a tényleges funkcionális elemek. Ezekre vonatkozó általános szabályok:

- **Kistárgyak (toggle, mini blokk):** `bg-white/60 p-5 rounded-2xl border border-slate-100 shadow-sm`
- **Szekció elválasztók:** `border-t border-slate-200/50 pt-6 mt-8`
- **Szekció fejlécek:** `text-sm font-bold text-slate-500 uppercase tracking-widest`

---

## 6. Összefoglalás — Más modulok átalakításának ellenőrző listája

Amikor egy meglévő modult (`laborModule`, stb.) átalakítasz erre a sablonra, ellenőrizd:

- [ ] A modul gyökérosztályai: `module-page w-full flex-col items-center justify-start pb-20 pt-8`
- [ ] A fejléc sáv `max-w-2xl mx-auto px-6` szélességgel rendelkezik
- [ ] A fejléc sáv belső eleme `flex items-start justify-between` (Lumina bal, Főoldal jobb)
- [ ] A Lumina felirat stílusa **szó szerint azonos** a főoldalon lévővel
- [ ] A Főoldal gomb mérete és stílusa **szó szerint azonos** a többi modulon lévővel
- [ ] A tartalom konténer osztályai: `space-y-8 w-full max-w-[500px] md:max-w-2xl mx-auto px-4 sm:px-6`
- [ ] A `w-full` osztály jelen van a tartalom konténerén (különben desktop-on balra csúszik!)
- [ ] A kártya alap osztályai: `glass-panel w-full rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden`
- [ ] A kártyán belül a tartalom egy `relative z-10` wrapperbe kerül
- [ ] A kártyán belüli fejléc `border-b border-indigo-50 mb-8` elválasztóval rendelkezik
- [ ] Nincsenek vízjelek, háttér-ikonok a kártyán belül
- [ ] A verziószám a kártya belső fejlécében van feltüntetve (pl. `V13.8`)
