# RFS bytel-isis

# Service ISIS – Projet NSO 

Ce projet NSO permet de gérer la configuration ISIS sur les routeurs
(Cisco, Nokia, Huawei) via des services NSO :

- **Service ISIS instance** : création / mise à jour d’une instance ISIS sur un device.
- **Inventaire ISIS instance** : modèle réutilisable contenant les paramètres communs.
- **Service ISIS interface** : activation d’ISIS sur les interfaces (commun / loopback), en option connecté à un inventaire.

Ce README se concentre sur **l’inventaire ISIS instance** et son utilisation.

------------------------------------------------

## 1. Inventaire ISIS instance – Principe

L’inventaire sert à définir un profil d’instance ISIS générique, par exemple :

- `area-id`
- `loopback0`
- plage SR (`sr lower-bound / upper-bound`)
- options LDP / MPLS / MPLS-SR-PREFER / DIST-LINK-STATE

Ensuite, le service ISIS instance sur un routeur donné référence simplement cet inventaire via `inventory-template`.  


------------------------------------------------

## 2. Exemple complet – Inventaire + Service

### 2.1. Création de l’inventaire ISIS instance

rfs inventory isis instance CISCO_INVENTORY
 area-id 99.600
 loopback0 192.168.1.31
 sr lower-bound 16000 upper-bound 23999
 ldp
 mpls
 mpls-sr-prefer
 dist-link-state

rfs isis CSGxxxx instance MY_INSTANCE
 inventory-template CISCO_INVENTORY

