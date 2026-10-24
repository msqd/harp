# Brainstorm explorations (2026-10-24)

Ordre : auth → audit → MCP → cache → dashboard (choix utilisateur : auth d'abord).

## Auth
- Public : petite équipe avec IdP existant, ou login/mot de passe dans HARP. Chaque méthode activée explicitement dans les settings.
- Mécanismes : login web + session, OIDC (SSO), jetons d'API. Basic reste une méthode, dépréciée au profit du login web.
- Droits : rôles fixes viewer / operator / admin.
- Rôle : en base, éditable dans l'UI.
- Mots de passe locaux : bootstrap en config, puis en base.
- Jetons d'API en base ; propriétaires humains et comptes service.
- Sessions : cookie signé sans état.
- MCP : Bearer d'abord, OAuth MCP (RFC 9728 + IdP) à explorer.
- Schéma DB à réfléchir fort : simple mais flexible ; table users existante (id, username(32), flags). L'utilisateur veut le voir en page visuelle.

Retours sur le schéma (page https://claude.ai/artifact/NgEfQqSKdHPpcmhcrFgxyp) :
- Tables préfixées auth_ (auth_users, auth_identities, auth_tokens).
- La nouvelle app harp_apps/auth reprend la table users existante (rename + migration).
- Recherches déléguées : pratiques des logiciels matures, littérature académique → explore/auth:explorations/auth/research/.

## Audit
- Périmètre : connexions, administration des accès, actions sur le trafic. Pas les lectures sensibles.
- Table en base + même événement en log JSON structuré (SIEM).
- App à part harp_apps/audit (tables audit_*), utile sans auth.
- Garanties : append-only, rétention configurable (janitor), chaîne de hash, écrit dans la transaction métier.
- Tensions pour le grill : (1) app à part qui écoute le bus d'événements contre écriture dans la même transaction métier : il faut un mécanisme d'écriture synchrone partagé ; (2) chaîne de hash avec plusieurs instances ou workers : sérialisation, ou une chaîne par instance.

## Cache explorer
- Vues : liste des entrées, détail d'une entrée, statistiques, lien transaction ↔ entrée.
- Index : table http_cache_entries (métadonnées en SQL, corps en blob).
- Invalidation : une entrée, préfixe d'URL, endpoint entier, tout le cache.
- Droits : rôle operator + événement d'audit ; sans auth, désactivée par défaut, ouvrable par un setting explicite.
- Liens : #801 (PURGE, primitive de suppression par clé), #1222, #1410.

## Dashboard
- Direction : converger vers lydia (front commun avec jaco).
- Douleurs : navigation et architecture, look & feel, dette technique. Surtout : le dashboard doit permettre de l'OLAP basique sur les données pour comprendre les requêtes. L'overview est trop synthétique, pas assez interactif, pas personnalisable.
- Coexistence : nouveau dashboard en parallèle sous /next, activé par un setting, bascule écran par écran.
- Timing : grillé en dernier ; auth, cache et audit se font d'abord dans le front actuel.

## MCP
- Streamable HTTP sous /mcp, port dashboard, derrière l'auth dashboard ; app optionnelle harp_apps/mcp.
- Outils v1, lecture seule : recherche de transactions, détail d'une transaction, état des endpoints. Pas la config système.
- OAuth MCP : IdP externe d'abord comme serveur d'autorisation (access token d'audience HARP → identity par (issuer, sub)), aucune table de plus. HARP serveur d'autorisation reste un ajout possible plus tard.
- Garde-fous : fenêtre de temps bornée, timeout SQL par requête, pas de full-text sur les corps, quota par session.
