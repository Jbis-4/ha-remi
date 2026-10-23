# Essai physique REMI — branche test/remi-final

Ce document prépare une installation future. Aucun déploiement, arrêt,
redémarrage, nettoyage du registre ou sauvegarde de production n'a été exécuté.
La sauvegarde ci-dessous reste à créer et à vérifier après validation.

## Contenu de la branche

Base : `main` local avec la conversion de température `(temp + 40) / 10`.
Les branches `fix/brightness-light` et `fix/rgb-entities` sont fusionnées.
Les conflits de `light.py`, tests, traductions et README sont résolus ensemble :

- Une lumière Brightness avec variateur, échelles HA 0–255 / REMI 0–100,
  commandes marche/arrêt et restauration de la dernière intensité non nulle.
- Une lumière RGB App Background Color, avec le même unique ID et le même
  comportement que l'ancienne Background Color.
- Aucun nouveau capteur de luminosité ambiante, aucun number Brightness et
  aucune entité Night Light ni écriture `lightnight`.
- Aucun module, appel ou import des diagnostics expérimentaux.

La branche de test retire les migrations automatiques du registre présentes
sur les branches de PR. Les branches de PR, `main` et la branche expérimentale
restent inchangées. Les tests fonctionnels sont conservés ; les assertions de
migration vérifient maintenant la conservation des anciennes entrées.

Les protections du client API déjà installées avec l'expérimentation sont
conservées ici, avec leurs tests, sans réintroduire le diagnostic : reconnexion
sans remplacement du réveil sélectionné, rejet d'une réponse d'un autre réveil,
et erreurs HTTP sans corps ni identifiant. Cela évite de perdre ces protections
lors du remplacement du dossier expérimental. Ce complément est propre à la
branche de test et n'a pas été ajouté aux deux branches de PR.

## Registre : ce qui change réellement

Les anciennes entrées number Brightness, sensor Luminosity et light Night Light
ne sont pas supprimées, renommées ou remappées automatiquement. Elles peuvent
rester visibles mais indisponibles. Les références des automatisations et les
historiques ne sont pas réécrits. Aucun accès direct aux fichiers `.storage`
n'est nécessaire pour l'installation.

Home Assistant enregistrera normalement la nouvelle lumière Brightness et
pourra mettre à jour le nom d'origine de Background Color. Il conserve ses
identifiants existants et les noms personnalisés. L'intensité précédente est
sauvegardée par le mécanisme RestoreEntity ; ce n'est pas une migration du
registre des entités.

**Comportement préexistant à connaître :** `switch.py` contient toujours un
`entity_registry.async_remove` pour l'interrupteur d'une alarme qui disparaît
entre deux réponses Event. Une réponse vide/incomplète pourrait donc faire
retirer un interrupteur d'alarme du registre local. Cette logique n'est pas
ajoutée par ces corrections, n'est pas une migration des lumières et ne supprime
pas l'alarme du serveur. Ne pas modifier les alarmes pendant cette campagne de
test ; garder la sauvegarde native comme retour arrière du registre.

Pour cette installation récente, le nettoyage manuel est suffisant : après
installation, retirer les anciennes entités dans l'interface Home Assistant,
ou supprimer puis réajouter les deux entrées REMI si aucune identité existante
ne doit être conservée. Cette dernière option supprime leurs associations
locales ; elle n'est pas nécessaire au fonctionnement des nouvelles lumières.

## Validation locale

Commande exécutée depuis le dépôt, dans l'environnement isolé existant :

```sh
.venv/test-env/bin/pytest -q --timeout=30
```

Résultat : **210 passed, 2 skipped, 1 xfailed, 1 xpassed**. Aucun échec bloquant.
`git diff --check` passe. Les tests couvrent les conversions, valeurs invalides,
services Home Assistant, cycles rapides variation/arrêt/marche, chargement d'une
intensité restaurée alors que l'état est éteint, conservation des anciennes
entrées du registre, identité de la couleur d'application et ciblage après
reconnexion. Tous les appels réseau de ces tests sont simulés.

Environnement de test : Python 3.12.3, Home Assistant 2025.1.4 (dépendances du
dépôt). Version lue sur la cible : Home Assistant 2026.10.2. La suite locale ne
remplace donc pas le contrôle de configuration et la validation sur cette cible.

## Paquet local préparé

Après le commit final, le paquet est construit uniquement à partir des fichiers
versionnés de cette branche, sans consulter ni copier le registre de production :

```sh
mkdir -p .venv/remi-final-build
git archive --format=tar.gz --output=.venv/remi-final-build/remi-final.tar.gz HEAD custom_components/urbanhello_remi_unofficial
```

`build-info.json` et `SHA256SUMS` dans le même dossier identifient le commit et
le contenu exacts. L'archive contient le chemin
`custom_components/urbanhello_remi_unofficial/`. Elle n'inclut ni tests, ni
`.storage`, ni secrets, ni anciens diagnostics, ni `__pycache__`.

## Installation future — seulement après accord

1. Créer une sauvegarde native HAOS incluant **Home Assistant et sa configuration**
   via Paramètres > Système > Sauvegardes. Vérifier sa fin, la télécharger hors
   de HA et conserver la clé du kit d'urgence si elle est chiffrée. Cette
   sauvegarde inclut le registre des entités, les entrées d'intégration et les
   données de restauration dans la configuration, ainsi que le code installé.
   Ne pas déposer cette sauvegarde ou sa clé dans Git.
2. Désactiver les loggers expérimentaux `inventory`, `normal`, `dark` et `direct`
   sous `custom_components.urbanhello_remi_unofficial.ambient_light_diagnostic`.
   Retirer uniquement leurs éventuelles déclarations DEBUG persistantes. Ne pas
   effectuer de mise à jour HACS de cette intégration pendant l'essai.
3. Extraire le paquet dans un dossier de préparation local au PC. Contrôler le
   SHA-256 et le commit avant toute copie. Ne pas utiliser une simple copie par
   dessus l'installation existante : elle laisserait les anciens modules.
4. Depuis le terminal HAOS/Supervisor, arrêter Core (`ha core stop`). Le terminal
   Supervisor et Samba doivent rester accessibles ; ne pas arrêter l'hôte.
5. Conserver le dossier installé complet dans un emplacement de sauvegarde
   **hors de `custom_components`**, par exemple
   `/config/remi-test-backups/<date>/urbanhello_remi_unofficial` côté HAOS.
   Le chemin Samba correspondant commence par `/mnt/homeassistant-prod/`.
6. Installer le dossier propre extrait du paquet à la place de
   `/mnt/homeassistant-prod/custom_components/urbanhello_remi_unofficial`.
   La sauvegarde de l'ancien dossier contient aussi les fichiers expérimentaux
   pour permettre un retour arrière de code.
7. Vérifier l'absence des fichiers `ambient_light_diagnostic.py`,
   `remi_inventory.py`, de leurs imports et de tous les anciens caches Python
   dans le nouveau dossier. Le contrôle actuel confirme leur présence dans
   l'installation ancienne ; le remplacement complet les retire. Les caches
   normaux seront recréés au démarrage.
8. Exécuter `ha core check` dans le terminal HAOS. En cas d'erreur, remettre
   l'ancien dossier avant de démarrer. Sinon, démarrer avec `ha core start`,
   puis consulter les journaux sans activer de traces HTTP ou de dumps API.
9. Nettoyer manuellement les entités obsolètes si souhaité, puis réaliser les
   essais ci-dessous. Aucune modification de `lightnight` sur UrbanHello n'est
   nécessaire. Ne pas publier les PR avant validation physique.

Les commandes `ha` sont destinées au terminal HAOS/Supervisor, pas à WSL.
Aucune des étapes ci-dessus n'a été exécutée lors de la préparation.

## Retour arrière

- **Code seulement, sans nettoyage local :** arrêter Core, déplacer le dossier
  de test hors de `custom_components`, remettre le dossier précédent complet,
  puis vérifier et redémarrer Core. La nouvelle entrée Brightness peut rester
  indisponible ; elle peut être retirée manuellement. Remettre seulement le code
  ne restaure pas un registre modifié entre-temps.
- **Retour exact incluant le registre**, notamment après suppression/réajout de
  l'intégration : restaurer la partie Home Assistant de la sauvegarde native
  avec les outils HAOS/Supervisor. Ne pas éditer ni recopier manuellement
  `.storage/core.entity_registry` ou les entrées de configuration. Une restauration
  de configuration rétablit aussi les autres changements locaux réalisés depuis
  la sauvegarde ; garder la fenêtre de test courte.
- La sauvegarde Home Assistant ne rétablit pas les réglages physiques conservés
  chez UrbanHello. Noter les niveaux et couleurs de départ localement ; les
  rétablir avec les commandes usuelles si nécessaire. Ne pas modifier d'alarmes.

Documentation : [sauvegardes et commandes HAOS](https://www.home-assistant.io/common-tasks/os/),
[kit d'urgence](https://www.home-assistant.io/more-info/backup-emergency-kit/).

## Vérification des deux réveils après installation

Pour chaque réveil, agir sur un seul à la fois et vérifier que l'autre ne change
pas. Aucun identifiant réel ou token ne doit apparaître dans le compte rendu.

- Température : comparer à nouveau avec le capteur indépendant.
- Brightness : 0/arrêt, une faible valeur non nulle, 50 % et 100 % ; vérifier la
  lumière supérieure, l'état HA, le variateur et l'application officielle.
- Variation puis arrêt/marche immédiats : retrouver la dernière intensité non
  nulle. Éteindre à 37 %, redémarrer HA normalement, puis allumer sans intensité
  et vérifier la restauration ; ne pas redémarrer HAOS ni les REMI pour ce test.
- App Background Color : vérifier que la couleur change dans l'application,
  sans la confondre avec la lumière physique. Vérifier l'identité conservée
  si l'intégration n'a pas été supprimée/réajoutée.
- Vérifier que les anciennes entités ne sont plus fonctionnelles et qu'aucune
  commande `lightnight` n'est émise. Les nettoyer dans l'interface si nécessaire.
- Vérifier volume, cadran et disponibilité, sans modifier les alarmes. Observer
  également le ciblage des deux réveils après une reconnexion naturelle.
