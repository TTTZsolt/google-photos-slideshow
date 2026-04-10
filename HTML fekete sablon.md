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

## 2. Elrendezés (Layout & Margins)

Minden oldalszélességet és margót a Slideshow Setup oldalhoz kell igazítani:
- **Külső konténer margója (Mobil):** `mx-6`
- **Külső konténer margója (Desktop):** `sm:mx-auto`
- **Fő konténer szélessége:** `max-w-2xl`
- **Belső doboz paddingja:** `p-8 sm:p-10`

---

## 3. Standard Fejléc Felépítés (Header)

A fejlécnek minden oldalon **fix pozícióban**, ugyanazzal az igazítással kell megjelennie, mint a Slideshow Setup oldalon. A Lumina felirat és a Ház ikon az oldal központi szélességéhez (`max-w-2xl`) igazodik.

```html
<header class="fixed top-0 left-0 w-full z-[100] pointer-events-none">
    <div class="max-w-2xl mx-6 sm:mx-auto py-4 flex items-center justify-between pointer-events-auto">
        <!-- Márkanév (Bal oldal) -->
        <span class="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500 tracking-tighter select-none leading-none">
            Lumina
        </span>

        <!-- Navigáció (Jobb oldal) -->
        <div class="flex items-center gap-3">
            <a href="/" class="p-2 rounded-xl text-slate-400 hover:text-white transition-all flex items-center justify-center">
                <i data-lucide="home" class="w-6 h-6 mt-2"></i>
            </a>
        </div>
    </div>
</header>
```

---

## 4. Görgetés és Magasság (Scrolling)

Az oldalnak görgethetőnek kell lennie, ha a tartalom nem fér el egy képernyőn.

- **Body:** Ne használj `overflow-hidden` szabályt a body-n!
- **Min-height:** Használj `min-h-screen` értéket a fő konténeren.

Az oldal tartalma egy középre igazított panelben legyen, amelynek margói és belső távolságai megegyeznek a Setup oldallal.

```html
<!-- Tartalmi távolság a fix fejléctől -->
<div class="mt-24 w-full max-w-2xl mx-6 sm:mx-auto">
    <div class="glass-panel rounded-3xl p-8 sm:p-10 shadow-2xl overflow-hidden">
        
        <!-- Cím Szekció -->
        <div class="relative z-10 w-full flex flex-col items-start mb-8">
            <h2 class="text-2xl font-bold text-slate-200 flex items-center gap-3">
                <i data-lucide="layout-template" class="text-indigo-500 w-7 h-7"></i>
                Oldal Neve <span class="text-[10px] text-indigo-400 font-black ml-1">V14.0</span>
            </h2>
            <p class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1 ml-10">
                Rövid leírás vagy állapotjelző
            </p>
        </div>

        <!-- Ide jön az oldal specifikus tartalma -->
        
    </div>
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
