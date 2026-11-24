# Préparation de synchronisation REMI — 24 novembre 2026

## État Git et périmètre

- Fork : `Jbis-4/ha-remi`, `main` et `origin/main` à `63eb3c8`.
- Amont : `timoa/ha-remi`, `upstream/main` à `034066f`, manifest 0.2.8.
- Les deux remotes ont été récupérés le 24 novembre 2026.
- Avant intervention : checkout propre, aucun stash, un seul worktree.
- Les historiques divergent de 5 commits propres au fork et 52 propres à l'amont.
  Les PR du fork #21, #22, #23 et #24 figurent dans l'historique officiel.
- Branche de préparation : `sync/upstream-main-2026-11-24`, créée depuis `main`.
- Fusion préparée avec `git merge --no-ff --no-commit upstream/main` : conflits
  résolus et résultat indexé, sans commit. Le futur commit de fusion conservera
  les deux historiques, sans rebase, squash ni cherry-pick des PR déjà intégrées.
- Aucun push, aucune fusion dans `main`, aucun déploiement, commande d'appareil,
  rechargement ou redémarrage de production.

Le dossier `.venv/` contient les environnements locaux de vérification, hors Git.
La branche `investigate/ambient-light-api` et les autres branches existantes
restent intactes. Le diagnostic expérimental n'est pas importé dans cette branche.

## Choix de synchronisation

| Domaine | Résultat préparé | Conséquence |
| --- | --- | --- |
| Deux REMI | Implémentation officielle : identifiant sélectionné conservé à la reconnexion, contrôle de l'identité de la réponse, verrou d'authentification par client | Les deux entrées restent indépendantes ; ajout de tests de chargement simultané |
| Alarmes | Champs officiels `event_time` et `recurrence`, nouvelles entités `time`, résolution des services à partir des entrées chargées | Édition heure/minute sans écraser les jours ; modification/suppression ciblées par identifiant d'alarme |
| Création d'alarme | Comportement officiel conservé : refus si plusieurs REMI sont chargés | Limitation fonctionnelle : créer dans l'application UrbanHello avec deux REMI ; aucun sélecteur ajouté dans cette synchronisation |
| Température | Formule officielle `(raw - 50) / 5`, décimales conservées et valeurs invalides inconnues | Remplace `(raw + 40) / 10` du fork ; valeur brute 160 : 22 °C au lieu de 20 °C |
| Luminosité physique | Curseur officiel `number`, échelle 0–100, champ API `luminosity` | Remplace la lumière graduable du fork ; aucune mesure en lux |
| Couleur | Entité officielle App Background Color conservée avec le même unique ID | Couleur dans l'application, pas une preuve de commande d'une lumière physique |
| Seuil sonore | Correctif officiel issu du fork, plage 0–250 | Conservé |
| Mode musique | Nouvelles options officielles Normal / Single track / Repeat track / Repeat playlist | Adapter les automatisations utilisant les anciens libellés |
| Firmware/cloud | Statut firmware affecté à l'appareil, bouton de vérification sans installation, timeout et reprises des lectures | Pas de répétition automatique des écritures après erreur réseau ou HTTP 5xx |

La nouvelle formule de température s'appuie sur les éléments d'interopérabilité
publiés par l'amont dans `docs/protocol-3.4.23.json`. Leur analyse Android n'a pas
été reproduite ici. Une conversion conforme à cette formule ne valide ni
l'étalonnage du capteur ni la température physique réelle.

Deux adaptations locales restent volontairement différentes de l'amont :

1. **Nettoyage manuel des anciennes entités.** Les anciennes entrées de registre
   luminosité/veilleuse ne sont pas supprimées au chargement. Les références
   doivent être migrées avant suppression dans l'interface HA. Garder une entrée
   ne conserve pas son ancienne implémentation : elle peut devenir indisponible.
   Le cycle normal des alarmes supprimées dans le cloud reste celui de l'amont.
2. **Messages d'erreur HTTP expurgés.** Les messages API n'incluent ni chemin
   contenant l'identifiant d'appareil ni corps HTTP. Les nouveaux mécanismes
   officiels de reconnexion et de reprise des lectures sont conservés.

Le code fonctionnel diffère ainsi de l'amont dans trois fichiers seulement :
`__init__.py`, `light.py` et `api.py`. Les tests et la documentation décrivent ces
différences. Les workflows CI, les traductions et les autres plateformes
reprennent l'amont. Le manifest conserve sa version 0.2.8 ; cette préparation ne
constitue pas une publication de version du fork.

## Conséquences pour l'installation existante

Une lecture ciblée du fichier de version, du manifest REMI et du registre
d'entités de production a trouvé HA **2026.11.2**, un manifest REMI **0.2.0**
(cette version seule n'identifie pas le code exact du fork), deux entrées REMI
représentées dans le registre et deux lumières Brightness activées dans le registre.
Cela ne prouve pas leur disponibilité instantanée dans HA.

Avant un éventuel déploiement autorisé :

1. Prévoir une sauvegarde native HA vérifiée et une copie privée du code installé.
2. Remplacer les usages de `light.*_brightness` par le nouveau `number` de chaque
   appareil, avec `number.set_value` et une valeur 0–100. Choisir les véritables
   entity IDs dans HA : ils ne sont pas déduits ni réservés par ce document.
3. `brightness_pct: 40` correspond à `value: 40`. `0` éteint la lumière supérieure.
   Un ancien attribut HA `brightness` sur 0–255 doit être converti en pourcentage.
   La restauration automatique de la dernière intensité non nulle disparaît.
4. Adapter les éventuels appels d'alarme ISO datetime à `HH:MM` ou `HH:MM:00`.
   L'heure reste locale au REMI. Les secondes non nulles sont refusées.
   Le paramètre `repeat` garde dimanche=0, puis est converti au tableau cloud
   commençant le lundi. Les attributs de jours affichés sont corrigés.
5. Adapter les éventuelles options du mode musique ; contrôler chaque entrée,
   les interrupteurs d'alarme, les nouvelles heures et les cartes de pièces.
6. Comparer les températures aux références physiques habituelles. L'historique
   n'est pas recalculé : un saut de courbe peut résulter du changement de formule.
7. Nettoyer les anciennes entités seulement après migration de leurs références,
   via l'interface HA, sans modification manuelle de `.storage`.

Aucune référence textuelle directe aux deux lumières Brightness ni aux sélecteurs
de mode musique n'a été trouvée dans les fichiers de production examinés :
`automations.yaml`, `scripts.yaml`, `scenes.yaml` et `.storage/lovelace*`.
La recherche ciblée dans le dépôt de configuration trouve les deux lumières dans
un instantané d'entités. Cela n'exclut pas les stratégies de dashboard dynamiques,
les scènes ou services ciblant un appareil/une zone, ni des configurations situées
hors de ces fichiers. Aucune configuration de production n'a été modifiée.

## Vérifications et limites

| Environnement isolé | Résultat |
| --- | --- |
| Python 3.14.2, HA 2026.10.4, banc officiel `pytest-homeassistant-custom-component==0.13.375` | 258 passed, 2 skipped, 1 XPASS ; couverture 97,51 % |
| Ancien environnement Python 3.12.3, HA 2025.1.4 | 258 passed, 2 skipped, 1 XFAIL, 1 XPASS |
| Python 3.14.2, HA 2026.11.2, essai Core sans plugin pytest | Réussite : deux entrées, huit plateformes, lectures indépendantes, luminosité, heure/interrupteur/modification/suppression d'alarme, refus de création ambiguë et déchargements |
| Contrôles statiques | `git diff --cached --check`, analyse syntaxique Python et lecture JSON : réussis |

Les deux skips sont hérités de l'amont, pour des setups de plateformes couverts
par les tests d'intégration ajoutés ou existants. Le XPASS est le test de création
d'entrée déjà marqué comme fragile par l'amont ; il réussit dans ces essais.

La version PyPI la plus récente du banc de test consultée est 0.13.375 ; elle
impose HA 2026.10.4. Forcer HA 2026.11.2 dans un second environnement expose deux
incompatibilités du **banc**, avant collecte des tests : ordre d'import de
`httpx2`, puis import de `_clear_logger_overwrites`, supprimé de HA.
Les dépendances du dépôt restent inchangées par ces essais de compatibilité.
L'essai Core utilise les vrais registres et services HA dans un dossier temporaire,
avec toutes les méthodes API REMI simulées. Ce n'est pas la suite pytest complète
sur 2026.11.2 et il ne valide pas les effets physiques.

Commandes reproductibles depuis la racine du dépôt, dans les environnements
correspondants :

```bash
.venv/sync-official/bin/python -m pytest -q --cov --cov-report=term-missing -r sX
.venv/test-env/bin/python -m pytest -q --disable-warnings -r sX
.venv/sync-ha-2026.11.2/bin/python -m tools.smoke_core
git diff --cached --check
```

`tests/test_two_remis.py` couvre le chargement simultané et les commandes par
les services HA. `tools/smoke_core.py` permet de refaire l'essai sans dépendre du
plugin pytest versionné. Les réponses et identifiants utilisés sont fictifs.
Les mécanismes de reconnexion et de rejet d'un autre appareil sont couverts par
les tests API officiels et les régressions locales conservées.

Aucune incompatibilité de chargement n'a été observée dans l'essai Core 2026.11.2.
La promesse ancienne « HA 2024.1 ou plus récent » n'est pas validée par ces tests
et n'est plus présentée comme garantie. HACS, Hassfest, la CI distante et la
validation physique sur les deux appareils n'ont pas été exécutés.

## Suite proposée, soumise à autorisation

Le résultat est indexé et la fusion reste en attente de commit sur la branche
temporaire. Proposition de message :
`Merge upstream main 034066f into REMI fork, preserving safe manual migration`.
Un accord distinct reste nécessaire pour intégrer dans `main`, pousser ou
déployer. Pour abandonner cette préparation sans autre changement ultérieur,
`git merge --abort` rétablit l'état d'avant fusion ; les nouveaux fichiers de
revue/test doivent être préservés séparément si l'on souhaite les conserver.

Le document `REMI_FINAL_TEST.md` décrit l'ancien essai du fork et reste une
archive ; sa formule de température et son variateur `light` ne décrivent pas
le résultat actuel.
