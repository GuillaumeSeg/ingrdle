# 🎮  INGRDLE

> **Daily game** — Devine l'ingrédient caché sur l'étiquette d'un produit réel.
> 3 produits/jour × 1 question "ingrédient fantôme" + trivia fun + score + streak.

---

## 📌 Concept

Chaque jour, **3 produits réels** (issus d'Open Food Facts) sont présentés.
Pour chaque produit, on affiche la liste des ingrédients avec **un trou**.
Le joueur doit deviner quel ingrédient manque parmi 4 options.

**MVP anglophone** (EN), V2 multilingue (FR, ES, DE…).

---

## 🎮 Mécanique

### "L'ingrédient fantôme"

- Image du produit + liste des ingrédients avec **1 ingrédient masqué**
- 4 options (1 vrai + 3 leurres plausibles)
- 5 essais max
- Après la réponse → **trivia fun** sur l'ingrédient

### Leurres (3 niveaux de fallback)

| Niveau | Méthode |
|--------|---------|
| 1 | Siblings via taxonomie OFF (`taxonomy_suggestions`) |
| 2 | Heuristique sur le slug (même suffixe : `-starch`, `-flour`, etc.) |
| 3 | Fallback random dans la même famille |

### Scoring

| Essai | Points |
|-------|--------|
| 1er | 128 |
| 2e | 64 |
| 3e | 32 |
| 4e | 16 |
| 5e | 8 |

- Score max/jour : **384 pts** (3 × 128)
- **Streak** : jours consécutifs (bonus +10% à 7 jours)
- "You beat X% of players today"

### V2 : Visuel "Foodie"

Une cellule/personnage qui se dégrade à chaque mauvais essai :
🟢 → 🟡 → 🟠 → 🔴 → ⚫

MVP : emoji uniquement. V2 : animation (Lottie/SVG).

---

## 📊 Données

### Source : [Open Food Facts](https://world.openfoodfacts.org)

- Licence : **ODbL** (libre)
- API gratuite, sans clé
- Export en masse : CSV/JSONL (~2-3 Go)
- Endpoint : `https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz`

### Filtres du pool

- `ingredients` ≥ 5
- `front_image_url` non vide
- `lang` = `en` (MVP)
- Catégories : snacks, céréales, sauces, boissons, biscuits, yaourts…
- Pool estimé : **5 000 – 15 000 produits** → 5-15 ans de contenu à 3/jour

---

## 🏗️ Architecture

┌─────────────────────────────────────────────────────────┐
│ PWA (SvelteKit + Tailwind) │
│ │
│ GET /questions_en.json (statique, servi par Netlify) │
│ Supabase SDK (auth + scores) │
└───────────┬───────────────────────────┬─────────────────┘
│ │
▼ ▼
┌─────────────────┐ ┌──────────────────┐
│ Netlify │ │ Supabase │
│ (static host) │ │ (free tier) │
│ │ │ │
│ questions.json │ │ users (id, │
│ (~50 Ko) │ │ username, │
│ │ │ streak) │
└─────────────────┘ │ scores (id, │
│ user_id, date, │
│ score, q1_pts, │
│ q2_pts, q3_pts)│
└──────────────────┘


**Aucun serveur codé.** Netlify sert le JSON statique. Supabase sert les scores.

---

## 📁 Structure du repo

ingrdle/
├── src/ # PWA (SvelteKit)
│ ├── routes/
│ │ ├── +layout.svelte
│ │ └── +page.svelte # Page principale du jeu
│ ├── lib/
│ │ ├── components/
│ │ │ ├── ProductCard.svelte
│ │ │ ├── IngredientList.svelte
│ │ │ ├── OptionsGrid.svelte
│ │ │ ├── ScoreBar.svelte
│ │ │ ├── StreakBadge.svelte
│ │ │ └── TriviaReveal.svelte
│ │ ├── stores/
│ │ │ ├── game.svelte.ts # State du jeu
│ │ │ └── user.svelte.ts # State utilisateur
│ │ └── supabase/
│ │ └── client.ts
│ ├── app.html
│ └── app.css
├── static/
│ ├── questions_en.json # 45 questions (15 jours × 3)
│ ├── questions_fr.json # V2
│ ├── manifest.webmanifest
│ └── icons/
├── scripts/
│ ├── prepare.py # Script principal (génère questions.json)
│ ├── generate_trivia.py # Appel LLM (OpenRouter)
│ ├── review.html # (Option B, plus tard)
│ └── data/
│ └── off_export.csv # (gitignored)
├── supabase/
│ └── migrations/
│ └── 001_init.sql # Tables users + scores
├── netlify.toml
├── .env # (gitignored)
├── .gitignore
├── package.json
├── svelte.config.js
├── tailwind.config.js
└── README.md


---

## 🐍 Pipeline de préparation (scripts Python)

### Étape 1 — Récupération & filtre

Télécharger l'export CSV OFF (~2 Go)
Filtre : len(ingredients) >= 5 AND front_image_url != ""
random.sample(qualifies_products, 45) → 15 jours × 3

### Étape 2 — Génération des questions

Pour chaque produit :
→ random.choice(ingredients) → ingrédient à cacher
→ Trouver 3 leurres (taxonomy / suffixe / random)
→ Stocker : { product, hidden, options[4], position, correct_index }


### Étape 3 — Trivia (LLM)

Pour chaque ingrédient unique (~45 pour le MVP) :
→ Appel OpenRouter (Claude Haiku 4.5 ou modèle :free)
→ Prompt : "Génère 5 faits fun, 1 phrase max, 1 emoji, ton décontracté"
→ Stocker dans trivia_raw.json (5 options par ingrédient)


### Étape 4 — Sélection manuelle (MVP)

Ouvrir trivia_raw.json dans l'éditeur
→ Lire les 5 trivia par ingrédient
→ Garder 1-2 (supprimer le reste)
→ Export trivia_final.json


### Format final : `questions_en.json`

```json
{
  "2026-10-09": [
    {
      "product_name": "Crepes Bretonnes 12x26.25g",
      "brand": "St Michel",
      "image_url": "https://images.openfoodfacts.org/...",
      "ingredients_display": ["wheat flour", "sugar", "???", "butter", "salt", "yeast"],
      "options": ["butter", "honey", "milk powder", "cocoa"],
      "correct_index": 0,
      "trivia": "🧈 Butter is 80% milk fat and 16% water. That's it. That's butter."
    }
  ]
}

🔐 Auth (MVP)
Pseudo choisi (1 champ, zéro friction) :

Premier visit → "Ton nom de joueur ?" → play
Stocké en localStorage + inséré dans Supabase users
Pas de login screen, pas de password
V2 : migration vers email + magic link (Supabase Auth)
🛡️ Sécurité
questions.json = public (volontaire)
Supabase RLS activé (un user ne voit pas les scores des autres)
HTTPS auto (Netlify)
Pas de données sensibles
MVP : rien à coder en sécurité supplémentaire
📦 Stack technique
Couche	Choix	Pourquoi
Frontend	SvelteKit + Tailwind CSS	Léger, rapide, parfait pour un jeu
Backend	Supabase (free tier)	DB + Auth + API REST + SDK, 0€
Hébergement	Netlify (free tier)	Auto-deploy via Git, commercial OK
Scripts	Python	Préprocessing, génération trivia
LLM	OpenRouter (Claude Haiku 4.5 ou :free)	Trivia, coût ~$0.05/batch
Domaine	Porkbun (~$12/an)	Optionnel, .netlify.app suffit pour MVP

Coûts totaux
Service	Coût
Netlify	$0
Supabase	$0
OpenRouter	~$0.05 (one-shot)
Domaine	~$12/an (optionnel)
TOTAL	$0 à $12/an

📅 Roadmap
MVP (4-6 semaines)
Semaine	Livrable
S1	Script Python + questions_en.json (15 jours) + trivia
S2	PWA : UI du jeu (produit, trou, options, scoring)
S3	Supabase : auth (pseudo) + scores + streak
S4	Polish + déploiement + test + promo

V2
Type "plus/moins" (variété de questions)
Leaderboard hebdo
Carte de partage (grille Wordle-like)
Animation "Foodie" (cellule qui dégrade)
Langue FR
Pool élargi + filtres par catégorie
PWA installable
V3
Modes saisonniers ("Semaine du chocolat")
Badges ("Additif Hunter", "Sugar Sniper")
Email + magic link (cross-device)
Mobile native (si besoin)
🎲 Aléatoire & fraîcheur
1 seed par jour (date) → tout le monde a les 3 mêmes produits
3 produits/jour → ~18 250 jours de contenu (50 ans)
Sélection : aléatoire dans le pool, filtré (≥5 ingrédients, image dispo)
📚 Références
Open Food Facts API : https://world.openfoodfacts.org/data
Export CSV : https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz
Supabase : https://supabase.com
Netlify : https://netlify.com
OpenRouter : https://openrouter.ai
Wordle clones Svelte (inspirations) :
https://github.com/jamesqquick/sveltekit-wordle-clone
https://github.com/dcBrian/wordle
✅ Décisions validées
Décision	Choix
Nom	ingrdle
Mécanique MVP	Ingrédient fantôme, 3 produits/jour
Score MVP	128/64/32/16/8 + emoji (🟢🟡🟠🔴⚫)
Score V2	Animation "Foodie"
LLM trivia	OpenRouter (Haiku 4.5 ou :free), 5 trivia/ingrédient, sélection manuelle
Données	Export OFF local, pré-traité en Python
Langue MVP	EN
Plateforme MVP	PWA web (SvelteKit)
Auth MVP	Pseudo choisi (1 champ)
Streak	Oui, dès le MVP
Carte de partage	V2
Hébergement	Netlify
DB	Supabase free tier
Domaine	Porkbun (optionnel)


© 2026 [Guillaume Se.]. All rights reserved.