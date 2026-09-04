# Document de cadrage — Projet "Second Cerveau" (veille personnelle)
### Binôme Fedi Mhenni / Azer Jouini — RNCP 39235/39635, Bloc 5

---

## 1. L'idée en une phrase

Une application de veille personnelle : je capte une source (URL), l'app la **qualifie**
(légitimité, intérêt, catégorie), la **range** (dossier + tags), la **digère** (résumé/synthèse
personnelle), et je la **republie** avec un vrai point de vue — personal branding ou posture
entreprise. Le but n'est pas d'accumuler du contenu (ça, ChatGPT ou NotebookLM le font déjà) mais
de **créer** : transformer une source en connaissance, puis en contenu à valeur ajoutée que je
publie vraiment.

Workflow : **Capter → Qualifier → Ranger → Digérer → Republier** — 5 étapes distinctes, chacune
son propre statut sur `Source`.

---

## 2. Le principe du binôme — à lire en premier, c'est le point le plus important

On développe **le même code, dans le même repo**, mais on est évalués **individuellement** par le
RNCP (chaque candidat est noté par compétence). Ça veut dire une séparation stricte entre ce qui
est commun et ce qui doit diverger entre nous deux :

| Élément | Commun (repo partagé) | Individuel (propre à chacun) |
|---|---|---|
| Code de l'application | ✅ | |
| Modèle de données / architecture | ✅ | |
| Document de cadrage (celui-ci) | ✅ (structure) | |
| Instance de l'app qui tourne | | ✅ chacun sa base SQLite, ses données |
| Sources captées | | ✅ chacun ses propres sources |
| Manifestation(s) professionnelle(s) | | ✅ chacun la ou les siennes |
| Republication LinkedIn/X réelle | | ✅ chacun son propre post, pas le même |
| Dossier de preuves PDF (Bloc 5) | | ✅ chacun le sien |
| Préparation de soutenance | | ✅ chacun la sienne |

**Pas de compte utilisateur ni d'authentification.** L'app est mono-utilisateur : chacun clone le
repo, fait tourner sa propre instance en local avec sa propre base, ses propres clés API. On ne
partage jamais de base de données ni de login.

Le jury va comparer les deux dossiers de preuves — il faut donc qu'on diverge sur les exemples
concrets (sources différentes, manifestation différente, republication différente), même si le
code et la structure du document sont partagés.

---

## 3. Modèle de données (commun — 7 tables)

- **Folder** — dossier thématique personnel (ex : Technique, Design & UX/UI, Carrière & Mindset,
  Tendances Numérique & IA, Gestion de projet digital). Le contenu des dossiers est propre à
  chaque instance, mais la structure de table est commune.
- **Source** — `url` (unique), `titre`, `contenu_brut`, `statut`
  (`captured|qualified|ranged|digested|published`), `folder_id`.
- **Qualification** — relation 1-1 avec Source : `categorie` (`metier|pro|perso|culture`),
  `legitimite`, `interet`, `qualified_by` (`ai|manual`).
- **Article** — contenu enrichi/traité issu d'une Source, relation 1-1 avec Source.
- **Tag** — `nom`.
- **ArticleTag** — table d'association explicite Article ↔ Tag (many-to-many) avec métadonnée
  `added_by` (`ai|manual`).
- **Republication** — `canal` (`linkedin|x`), `brouillon`, `statut` (`draft|published`),
  `posture` (`personal_branding|entreprise`).

---

## 4. Architecture (commun)

```
app/
  models/     # SQLAlchemy — un fichier par entité
  routes/     # endpoints FastAPI, appellent les services, jamais de logique métier
  services/   # logique métier (capture, qualify, tagging, republish, llm_provider)
  templates/  # Jinja2, server-rendered
config.py
scripts/seed.py
tests/
docs/CADRAGE.md   # contexte condensé, lu automatiquement par les assistants de code
```

- **SQLite**, pas PostgreSQL — chacun sa base locale, pas de serveur à administrer.
- **Jinja2** server-rendered, pas de frontend séparé (React/Vue) — pas nécessaire pour la
  complexité du projet, et ça réduit la surface technique dans un délai court.
- **LLM = Google Gemini**, appelé en HTTP direct (pas de SDK), derrière une abstraction
  `LLMProvider` avec repli automatique sur un `MockProvider` si l'appel échoue ou si aucune clé
  n'est configurée — le flux applicatif ne casse jamais à cause d'un appel IA raté.
- **Docker + docker-compose** pour que le code tourne à l'identique sur les deux machines.
- **Pas d'API d'auto-publication LinkedIn/X** — les délais de validation d'app de ces plateformes
  dépassent largement la durée du projet. La republication produit un brouillon éditable ; la
  vraie publication se fait manuellement (copier/coller) par chacun.

---

## 5. Git — discipline de travail (commun)

- Repo unique, `main` toujours fonctionnel.
- Scaffold/configuration pure (Docker, dépendances, `.gitignore`) : commit direct sur `main`,
  pas besoin de PR — rien à réviser sur du config standard.
- Dès qu'il y a de la vraie logique (modèles, routes, services) : branche dédiée
  (`feature/nom-de-la-brique`), petits commits (un changement logique cohérent par commit, pas un
  commit par ligne), puis PR vers `main` avant merge — même en solo, on se relit soi-même dans
  l'interface avant de merger.
- `.env`, `*.db`, `__pycache__/`, `venv/` jamais commités.
- Un fichier `CLAUDE.md` à la racine encode ces règles pour l'assistant de code local (Claude
  Code) : une brique à la fois, explique avant de coder, jamais de commit direct sur `main` pour
  du code métier, commente les lignes Python non triviales.

---

## 6. Plan de sprints (commun pour le code, avec répartition)

| Sprint | Objectif | Livrable | Ensemble ou séparé |
|---|---|---|---|
| Sprint 0 | Repo, scaffold FastAPI, Docker, `GET /` → 200 sur les deux machines | Squelette qui tourne chez les deux | Ensemble (config partagée) |
| Sprint 1 | Modèle de données complet (7 tables) + script de seed des dossiers | Modèles + DB initialisée | Ensemble — fondation critique, une erreur ici se répercute partout |
| Sprint 1 (suite) | Routes de capture (URL) + templates de base (dashboard, formulaire, liste) | Capture fonctionnelle | Peut se paralléliser |
| Sprint 2 | Abstraction `LLMProvider` (Gemini) + service de qualification + édition manuelle | Qualification fonctionnelle | Peut se paralléliser (1 pers. provider, 1 pers. UI) |
| Sprint 2 (suite) | Service de rangement (dossier + tags) + édition manuelle des tags | Rangement fonctionnel | Peut se paralléliser |
| Sprint 2 (fin) | Service de digestion (résumé) + test bout en bout capté→digéré | Digestion fonctionnelle | Ensemble pour l'intégration |
| Sprint 3 | Service de republication (2 postures) + brouillon éditable + bouton copier | Republication fonctionnelle | Peut se paralléliser |
| Sprint 3 (fin) | Polish UI sobre, page "Mes republications", **publication réelle test** | UI finalisée | Ensemble |
| Sprint 4 | Nettoyage code, relecture croisée, CI/CD si le temps permet, remplissage dossiers de preuves | Repo propre + dossiers Bloc 5 individuels | Ensemble pour le code, séparé pour les dossiers |
| Bonus (si le temps le permet) | Agent quotidien RSS (script + cron, pas de scheduler applicatif) | Sources captées automatiquement | Séparé (chacun ses flux RSS) |

**Règle de coupe si retard** (dans cet ordre, ne jamais sacrifier le socle) :
1. Couper d'abord : CI/CD (GitHub Actions) — optionnel depuis le début.
2. Couper ensuite : déploiement en ligne — la démo peut se faire en local.
3. Couper ensuite : polish visuel avancé, agent RSS quotidien — le socle sobre suffit.
4. **Ne jamais couper** : Qualifier / Ranger / Digérer / Republier avec une vraie republication —
   c'est le socle noté.

---

## 7. Ce que CHACUN doit produire individuellement

Cette partie est personnelle — chacun remplit la sienne, avec ses propres exemples.

1. **Faire tourner sa propre instance** : cloner le repo, sa propre base SQLite, ses propres clés
   API (Gemini), sans jamais partager de données avec l'autre.
2. **Capter ses propres sources**, réparties sur ses propres dossiers thématiques. Prévoir
   explicitement une catégorie **"Gestion de projet digital"** — c'est ce qui couvre la compétence
   RNCP "observer/analyser l'évolution de la gestion de projet digital" (ME5.1), sinon ce point
   de la grille reste sans preuve.
3. **S'appuyer sur les recommandations du CIGREF** pour justifier le choix de ses médias/canaux de
   veille (ME5.1) — présenter 4 à 6 recommandations CIGREF et les relier concrètement à sa propre
   pratique de veille dans le projet.
4. **Participer à au moins une manifestation professionnelle réelle** (salon, meetup, conférence,
   webinar) et en garder une **preuve visuelle** (photo, badge, story) — pas seulement un texte
   descriptif, le jury peut demander une preuve tangible de présence.
5. **Republier réellement** au moins un contenu sur LinkedIn ou X, avec un vrai point de vue (pas
   un résumé), et si possible dans les deux postures : personal branding (compétence "méthodes de
   conseil") et posture entreprise (compétence "réflexion stratégique interne/client").
6. **Rédiger son propre dossier de preuves Bloc 5** (PDF individuel), structuré par exemple ainsi :
   Introduction → Partie 1 (sources par catégorie de veille + une analyse détaillée par catégorie)
   → Partie 2 (CIGREF) → Partie 3 (manifestation professionnelle) → Partie 4 (posture de conseil /
   innovation numérique) → Conclusion.
7. **Préparer sa propre soutenance** : pitch personnel, script de démo sur sa propre instance,
   réponses aux questions probables du jury, avec ses propres exemples concrets appris par cœur.

---

## 8. Lien avec le Bloc 5 RNCP (individuel, chacun sur sa propre grille)

| Compétence | Ce qu'il faut comme preuve |
|---|---|
| ME5.1 — Sélectionner médias/canaux de veille en tenant compte des recommandations du CIGREF | Dossier de preuves Partie 1 + 2 (sources justifiées + section CIGREF) |
| ME5.1 — Observer/analyser l'évolution de la gestion de projet digital | Catégorie de veille dédiée "Gestion de projet digital" avec analyse d'évolution dans le temps, pas juste une liste de sources |
| ME5.2 — Participer à des manifestations professionnelles | Preuve de présence réelle (texte + visuel) |
| ME5.2 — Contribuer à la réflexion stratégique interne/client | Republication posture "entreprise", ou une analyse explicitement tournée vers un usage interne/client |
| ME5.2 — Mettre en œuvre des méthodes de conseil | Analyse d'un problème réel rencontré sur l'app + solution proposée + posture de conseil assumée |

Deux livrables écrits séparés sont normalement encore attendus en plus du dossier de preuves : une
note de synthèse ME5.1 et un compte-rendu ME5.2 (souvent intégré au rapport de stage) — à vérifier
précisément avec le prof, mais ce document + le dossier de preuves individuel en sont la base.

---

## 9. Décisions actées (à ne pas remettre en question sans le signaler à l'autre)

| Décision | Raison |
|---|---|
| Pas d'authentification / compte utilisateur | App personnelle mono-utilisateur, le binôme porte sur le code, pas sur une base partagée |
| Pas d'API d'auto-publication LinkedIn/X | Délai de validation d'app supérieur à la durée du projet ; la vraie valeur, c'est le contenu publié réellement, pas l'automatisation du post |
| SQLite plutôt que PostgreSQL | Instance locale personnelle, pas de serveur à administrer |
| Jinja2 plutôt que React/Vue | App server-rendered, pas de besoin d'interactivité complexe côté client dans ce délai |
| LLM Gemini uniquement (pas de multi-provider) | Simplifie le développement, une seule clé à gérer, `MockProvider` en repli si besoin |
| Docker + docker-compose | Garantit que le code tourne à l'identique chez les deux |
| Ranger et Digérer séparés en deux étapes distinctes | Rend la compétence "digestion" démontrable indépendamment du simple classement |

---

## 10. Checklist finale avant remise

- [ ] Les deux instances tournent indépendamment, chacune avec ses propres données
- [ ] Chaque dossier de preuves individuel est complet et illustré (captures d'écran, preuve de
      manifestation, republication réelle)
- [ ] Le code est propre, sur `main`, avec un historique Git lisible (petits commits, PR sur la
      logique métier)
- [ ] Chacun a répété son pitch et son script de démo sur sa propre instance
