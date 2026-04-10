# Lumina - Dark UI Design System (V14.0)

Ez a dokumentum rögzíti a Lumina alkalmazás dark-mode (fekete alapú) felületi irányelveit, a `receiver.html` mintájára.

## 1. Alapvető Stílusjegyek (CSS Tokens)

A stílus alapja a **TailwindCSS**, kiegészítve egyedi üveg-effektusokkal és prémium gradiensekkel.

### Színpaletta
- **Background:** `bg-[#020617]` (Mélyfekete/Sötétkék)
- **Primary Accent:** `from-indigo-600 to-purple-600` (Gradiens)
- **Secondary Accent:** `text-indigo-400`
- **Text:** `text-slate-200` (Főszöveg), `text-slate-400` (Másodlagos / Ikonok)

---

## 2. Elrendezés (Layout & Width)

Minden oldalszélességet a Slideshow Setup oldalhoz kell igazítani:
- **Fő konténer:** `max-w-2xl mx-auto`
- **Tartalom:** `w-full px-6`

---

## 3. Standard Fejléc Felépítés (Header)

A fejlécnek minden oldalon **fix pozícióban**, ugyanazzal a magassággal és margóval kell megjelennie.

```html
<header class="fixed top-0 left-0 w-full z-[100] px-6 py-4 flex items-center justify-between pointer-events-none">
    <!-- Márkanév (Bal oldal) - Mindig aktív -->
    <div class="pointer-events-auto">
        <span class="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500 tracking-tighter select-none leading-none">
            Lumina
        </span>
    </div>

    <!-- Navigáció (Jobb oldal) -->
    <div class="flex items-center gap-3 pointer-events-auto">
        <a href="/" class="p-2 rounded-xl text-slate-400 hover:text-white transition-all flex items-center justify-center">
            <i data-lucide="home" class="w-6 h-6 mt-2"></i>
        </a>
    </div>
</header>

<!-- Tartalmi távolság a fix fejléctől -->
<div class="mt-24"></div>
```

---

## 4. Oldal Címe (Page Title)

Az oldal neve (pl. Szortírozó) ne a Lumina alá kerüljön, hanem a fő tartalmi területen jelenjen meg címként, Lucide ikonnal kiegészítve.

```html
<div class="w-full flex flex-col items-start mb-6">
    <h1 class="text-2xl font-bold text-slate-200 flex items-center gap-3">
        <i data-lucide="layout-template" class="text-indigo-500 w-7 h-7"></i>
        Oldal Neve <span class="text-[10px] text-indigo-400 font-black ml-1">V14.0</span>
    </h1>
    <p class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1 ml-10">
        Rövid leírás vagy állapotjelző
    </p>
</div>
```

---

## 3. Gombok és Interakciók

### Fő Akciógomb (Primary Button)
A gombok legyenek szélesek, lekerekítettek, és használják a márka gradienst.

```html
<button class="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-10 py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition shadow-lg whitespace-nowrap">
    <i data-lucide="shuffle" class="w-4 h-4"></i>
    Szöveg Helye
</button>
```

---

## 4. Tipográfia és Ikonográfia

- **Betűtípus:** `Outfit` vagy `Inter` (Sans-serif)
- **Ikonok:** `Lucide Icons` (vékony, modern vonalvezetés)
- **Verziószám:** Mindig apró, indigo színű felsőindex vagy címke: `<span class="text-[10px] text-indigo-400 font-black ml-1">V14.0</span>`

---

## 5. Elrendezési Szabályok (Layout)

1. **Zéró Padding a Széleken:** A tartalom (pl. vetítés) érjen ki a széléig, ha szükséges.
2. **Központosított Modulok:** A beállító ablakok (Setup Modals) legyenek középre igazítva, nagy lekerekítéssel (`rounded-3xl`).
3. **Sötét Overlay:** Modulok alatt használjunk `backdrop-blur-md` és `bg-black/60` réteget.
