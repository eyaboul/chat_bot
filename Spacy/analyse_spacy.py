'''
import spacy
import pandas as pd

def main():
    # Charger le modèle spaCy avec vecteurs Word2Vec
    # 'en_core_web_md' est un modèle pré-entrainé de spaCy qui contient des vecteurs de mots.
    nlp = spacy.load("en_core_web_md")

    # Lire le fichier CSV sans en-tête (le fichier contient juste des logs, sans colonne de nom)
    # header=None indique qu'il n'y a pas d'en-tête dans le fichier CSV

    # Parcourir chaque log dans la première colonne (df[0] fait référence à la première colonne sans nom)
    # Chaque ligne du fichier correspond à un log que nous allons analyser
    for text in df[0]:
        # Analyser chaque log avec spaCy. Cela crée un objet 'doc' contenant toutes les informations NLP.
        doc = nlp(text)

        # Afficher le texte du log que nous analysons
        print(f"\nTexte : {text}")

        # Identifier et afficher les entités nommées (comme les dates, les adresses IP, les noms, etc.)
        # Chaque entité détectée par spaCy est affichée avec son type (personne, organisation, etc.)
        for ent in doc.ents:
            print(f" - Entité : {ent.text} | Type : {ent.label_}")

        # ================================
        # Traitement de texte avec spaCy
        # ================================

        # === Tokenisation ===
        # Afficher chaque token du texte. Un token peut être un mot, un symbole, ou même une ponctuation.
        print("\n=== [Tokenisation] ===")
        for token in doc:
            print(f"Token: {token.text}")

        # === Part-of-Speech Tagging ===
        # Afficher le rôle grammatical de chaque token : nom, verbe, adjectif, etc.
        print("\n=== [Part-of-Speech Tagging] ===")
        for token in doc:
            print(f"Token: {token.text} | POS: {token.pos_} | Lemma: {token.lemma_}")
            # Lemma : forme de base du mot (par exemple, "manger" au lieu de "mange" ou "mangeant")

        # === Named Entity Recognition ===
        # Afficher les entités nommées détectées dans le texte, comme les dates, personnes, etc.
        print("\n=== [Named Entity Recognition] ===")
        for ent in doc.ents:
            print(f"Entité: {ent.text} | Type: {ent.label_}")

        # === Dependency Parsing ===
        # Analyser la relation entre chaque mot (qui dépend de qui dans la phrase)
        # Exemple : "manger" dépend de "je" dans "je mange une pomme"
        print("\n=== [Dependency Parsing] ===")
        for token in doc:
            print(f"Mot: {token.text} | Rôle: {token.dep_} | Attaché à: {token.head.text}")
            # token.dep_ : le rôle grammatical du mot (ex. sujet, objet)
            # token.head.text : le mot auquel le token est lié grammaticalement (le "chef")

        # ================================
        # Génération de vecteurs Word2Vec
        # ================================

        # Vérifier si le modèle spaCy a généré des vecteurs pour le texte
        # Si les vecteurs sont disponibles, les afficher. Ces vecteurs permettent de mesurer la similarité entre mots.
        print("\n=== [Word2Vec Embedding] ===")
        if doc.vector_norm:  # Vérifie si des vecteurs sont disponibles
            print(f"Vecteur du document (tail taille {len(doc.vector)}):")
            print(doc.vector)  # Affiche le vecteur global du texte
        else:
            print("Aucun vecteur disponible avec ce modèle pour le texte donné.")

        # Exemple : comparer la similarité entre les deux premiers tokens du texte (si possible)
        if len(doc) >= 2 and doc[0].has_vector and doc[1].has_vector:
            sim = doc[0].similarity(doc[1])  # Mesure de la similarité entre deux tokens
            print(f"\nSimilarité entre '{doc[0].text}' et '{doc[1].text}' : {sim:.3f}")
        else:
            print("Impossible de comparer des tokens : vecteurs non disponibles.")

def get_log_vectors(logs):
    nlp = spacy.load("en_core_web_md")
    vectors = []
    for log in logs:
        doc = nlp(log)
        vectors.append(doc.vector)
    return vectors
    
def clean(title):
    	df = pd.read_csv(title , sep="," , header=None , on_bad_lines='skip')
    	df.dropna(axis=1, how='all', inplace=True)
    	df.columns = df.iloc[0]
    	df = df[1:].reset_index(drop=True)
    	
    	colonnes_importantes=['@timestamp', 'agent.hostname', 'agent.name', 'agent.name.text', 'agent.type', 'agent.version', 'cisco.ios.facility', 'cisco.ios.message_count', 'client.address', 'component.binary', 'component.dataset', 'component.id', 'component.type', 'container.id', 'data_stream.dataset', 'data_stream.namespace', 'data_stream.type', 'destination.bytes', 'destination.ip', 'destination.mac', 'destination.packets', 'destination.port', 'ecs.version', 'elastic.agent.id', 'elastic_agent.id', 'elastic_agent.snapshot', 'elastic_agent.version', 'error.message', 'error.type', 'event.agent_id_status', 'event.code', 'event.created', 'event.dataset', 'event.duration', 'event.end', 'event.id', 'event.ingested', 'event.kind', 'event.module', 'event.provider', 'event.sequence', 'event.start', 'event.timezone', 'file.Ext.entropy', 'file.Ext.header_bytes', 'file.extension', 'file.name', 'host.containerized', 'host.domain', 'host.hostname', 'host.id', 'host.ip', 'host.mac', 'host.name', 'host.name.text', 'host.os.Ext.variant', 'host.os.build', 'host.os.codename', 'host.os.family', 'host.os.full', 'host.os.full.caseless', 'host.os.full.text', 'host.os.kernel', 'host.os.name', 'host.os.name.caseless', 'host.os.name.text', 'host.os.platform', 'host.os.type', 'host.os.version', 'http.request.body.bytes', 'http.request.id', 'http.request.method', 'http.response.body.bytes', 'http.response.status_code', 'http.version', 'id', 'input.type', 'log.file.device_id', 'log.file.idxhi', 'log.file.idxlo', 'log.file.inode', 'log.file.path', 'log.file.vol', 'log.logger', 'log.offset', 'log.origin.file.line', 'log.origin.file.name', 'log.origin.function', 'log.source', 'log.source.address', 'log.syslog.priority', 'message', 'network.bytes', 'network.community_id', 'network.direction', 'network.iana_number', 'network.packets', 'network.transport', 'network.type', 'network_traffic.flow.final', 'network_traffic.flow.id', 'observer.product', 'observer.type', 'observer.vendor', 'process.Ext.code_signature', 'process.code_signature.exists', 'process.code_signature.status', 'process.code_signature.subject_name', 'process.code_signature.trusted', 'process.entity_id', 'process.executable', 'process.executable.caseless', 'process.executable.text', 'process.name', 'process.name.caseless', 'process.name.text', 'process.parent.pid', 'process.pid', 'process.thread.id', 'related.ip', 'related.user', 'server.address', 'service.name', 'service.type', 'source.bytes', 'source.ip', 'source.mac', 'source.packets', 'source.port', 'state', 'syslog.facility', 'syslog.facility_label', 'syslog.priority', 'tags', 'tls.established', 'url.full', 'url.full.text', 'user.domain', 'user.id', 'user.name', 'user.name.text', 'winlog.activity_id', 'winlog.api', 'winlog.channel', 'winlog.computer_name', 'winlog.event_data.AccessList', 'winlog.event_data.AccessListDescription', 'winlog.event_data.AccessMask', 'winlog.event_data.AccessMaskDescription', 'winlog.event_data.AuthenticationPackageName', 'winlog.event_data.Binary', 'winlog.event_data.Direction', 'winlog.event_data.ElevatedToken', 'winlog.event_data.FilterRTID', 'winlog.event_data.HandleId', 'winlog.event_data.KeyLength', 'winlog.event_data.LayerName', 'winlog.event_data.LayerNameDescription', 'winlog.event_data.LayerRTID', 'winlog.event_data.LogonProcessName', 'winlog.event_data.LogonType', 'winlog.event_data.ObjectName', 'winlog.event_data.ObjectServer', 'winlog.event_data.ObjectType', 'winlog.event_data.PrivilegeList', 'winlog.event_data.ProcessID', 'winlog.event_data.ProcessId', 'winlog.event_data.ProcessName', 'winlog.event_data.Protocol', 'winlog.event_data.RemoteMachineDescription', 'winlog.event_data.RemoteMachineID', 'winlog.event_data.RemoteUserDescription', 'winlog.event_data.RemoteUserID', 'winlog.event_data.RestrictedSidCount', 'winlog.event_data.SourceHandleId', 'winlog.event_data.SourceProcessId', 'winlog.event_data.SubjectDomainName', 'winlog.event_data.SubjectLogonId', 'winlog.event_data.SubjectUserName', 'winlog.event_data.SubjectUserSid', 'winlog.event_data.TargetDomainName', 'winlog.event_data.TargetHandleId', 'winlog.event_data.TargetLinkedLogonId', 'winlog.event_data.TargetLogonId', 'winlog.event_data.TargetProcessId', 'winlog.event_data.TargetUserName', 'winlog.event_data.TargetUserSid', 'winlog.event_data.VirtualAccount', 'winlog.event_data.param1', 'winlog.event_data.param2', 'winlog.event_id', 'winlog.keywords', 'winlog.logon.id', 'winlog.logon.type', 'winlog.opcode', 'winlog.process.pid', 'winlog.process.thread.id', 'winlog.provider_name', 'winlog.record_id', 'winlog.task', 'event.severity', 'event.category', 'event.type', 'event.action' , 'syslog.severity_label', 'log.level']
    	
    	df['severity_unified'] = df['log.level'].where(df['log.level'] != '-', df['syslog.severity_label'])
    	# Affichage des 200 premières lignes des colonnes importantes + la nouvelle colonne
    	colonnes_affichage = colonnes_importantes + ['severity_unified']
    	print(df[colonnes_affichage].head(200))
    	
    	#print(df[colonnes_importantes].head(200))

    	return df

if __name__ == "__main__":
    clean("logs.csv")
'''



import spacy
import pandas as pd

def clean(title):
    # Lire le fichier CSV en ignorant les lignes mal formées
    df = pd.read_csv(title, sep=",", header=None, on_bad_lines='skip')
    # Supprimer les colonnes complètement vides
    df.dropna(axis=1, how='all', inplace=True)
    # Utiliser la première ligne comme noms de colonnes
    df.columns = df.iloc[0]
    # Supprimer cette ligne d'en-tête des données
    df = df[1:].reset_index(drop=True)
    
    # Liste des colonnes importantes à conserver
    colonnes_importantes = [
        '@timestamp', '_score', 'agent.hostname', 'agent.name', 'agent.name.text', 'agent.type', 'agent.version',
        'cisco.ios.facility', 'cisco.ios.message_count', 'client.address', 'component.binary',
        'component.dataset', 'component.id', 'component.type', 'container.id', 'data_stream.dataset',
        'data_stream.namespace', 'data_stream.type', 'destination.bytes', 'destination.ip',
        'destination.mac', 'destination.packets', 'destination.port', 'ecs.version', 'elastic.agent.id',
        'elastic_agent.id', 'elastic_agent.snapshot', 'elastic_agent.version', 'error.message',
        'error.type', 'event.agent_id_status', 'event.code', 'event.created', 'event.dataset',
        'event.duration', 'event.end', 'event.id', 'event.ingested', 'event.kind', 'event.module',
        'event.provider', 'event.sequence', 'event.start', 'event.timezone', 'file.Ext.entropy',
        'file.Ext.header_bytes', 'file.extension', 'file.name', 'host.containerized', 'host.domain',
        'host.hostname', 'host.id', 'host.ip', 'host.mac', 'host.name', 'host.name.text',
        'host.os.Ext.variant', 'host.os.build', 'host.os.codename', 'host.os.family',
        'host.os.full', 'host.os.full.caseless', 'host.os.full.text', 'host.os.kernel',
        'host.os.name', 'host.os.name.caseless', 'host.os.name.text', 'host.os.platform',
        'host.os.type', 'host.os.version', 'http.request.body.bytes', 'http.request.id',
        'http.request.method', 'http.response.body.bytes', 'http.response.status_code', 'http.version',
        'id', 'input.type', 'log.file.device_id', 'log.file.idxhi', 'log.file.idxlo',
        'log.file.inode', 'log.file.path', 'log.file.vol', 'log.logger', 'log.offset',
        'log.origin.file.line', 'log.origin.file.name', 'log.origin.function', 'log.source',
        'log.source.address', 'log.syslog.priority', 'message', 'network.bytes', 'network.community_id',
        'network.direction', 'network.iana_number', 'network.packets', 'network.transport',
        'network.type', 'network_traffic.flow.final', 'network_traffic.flow.id', 'observer.product',
        'observer.type', 'observer.vendor', 'process.Ext.code_signature',
        'process.code_signature.exists', 'process.code_signature.status',
        'process.code_signature.subject_name', 'process.code_signature.trusted', 'process.entity_id',
        'process.executable', 'process.executable.caseless', 'process.executable.text',
        'process.name', 'process.name.caseless', 'process.name.text', 'process.parent.pid',
        'process.pid', 'process.thread.id', 'related.ip', 'related.user', 'server.address',
        'service.name', 'service.type', 'source.bytes', 'source.ip', 'source.mac',
        'source.packets', 'source.port', 'state', 'syslog.facility', 'syslog.facility_label',
        'syslog.priority', 'tags', 'tls.established', 'url.full', 'url.full.text',
        'user.domain', 'user.id', 'user.name', 'user.name.text', 'winlog.activity_id',
        'winlog.api', 'winlog.channel', 'winlog.computer_name', 'winlog.event_data.AccessList',
        'winlog.event_data.AccessListDescription', 'winlog.event_data.AccessMask',
        'winlog.event_data.AccessMaskDescription', 'winlog.event_data.AuthenticationPackageName',
        'winlog.event_data.Binary', 'winlog.event_data.Direction', 'winlog.event_data.ElevatedToken',
        'winlog.event_data.FilterRTID', 'winlog.event_data.HandleId', 'winlog.event_data.KeyLength',
        'winlog.event_data.LayerName', 'winlog.event_data.LayerNameDescription',
        'winlog.event_data.LayerRTID', 'winlog.event_data.LogonProcessName',
        'winlog.event_data.LogonType', 'winlog.event_data.ObjectName',
        'winlog.event_data.ObjectServer', 'winlog.event_data.ObjectType',
        'winlog.event_data.PrivilegeList', 'winlog.event_data.ProcessID',
        'winlog.event_data.ProcessId', 'winlog.event_data.ProcessName',
        'winlog.event_data.Protocol', 'winlog.event_data.RemoteMachineDescription',
        'winlog.event_data.RemoteMachineID', 'winlog.event_data.RemoteUserDescription',
        'winlog.event_data.RemoteUserID', 'winlog.event_data.RestrictedSidCount',
        'winlog.event_data.SourceHandleId', 'winlog.event_data.SourceProcessId',
        'winlog.event_data.SubjectDomainName', 'winlog.event_data.SubjectLogonId',
        'winlog.event_data.SubjectUserName', 'winlog.event_data.SubjectUserSid',
        'winlog.event_data.TargetDomainName', 'winlog.event_data.TargetHandleId',
        'winlog.event_data.TargetLinkedLogonId', 'winlog.event_data.TargetLogonId',
        'winlog.event_data.TargetProcessId', 'winlog.event_data.TargetUserName',
        'winlog.event_data.TargetUserSid', 'winlog.event_data.VirtualAccount',
        'winlog.event_data.param1', 'winlog.event_data.param2', 'winlog.event_id',
        'winlog.keywords', 'winlog.logon.id', 'winlog.logon.type', 'winlog.opcode',
        'winlog.process.pid', 'winlog.process.thread.id', 'winlog.provider_name',
        'winlog.record_id', 'winlog.task', 'event.severity', 'event.category',
        'event.type', 'event.action', 'syslog.severity_label', 'log.level'
    ]
    
    # Fusionner log.level et syslog.severity_label dans une seule colonne
    df['severity_unified'] = df['log.level'].where(df['log.level'] != '-', df['syslog.severity_label'])
    
    # Affichage des 200 premières lignes des colonnes importantes + la nouvelle colonne
    colonnes_affichage = colonnes_importantes + ['severity_unified']
    print(df[colonnes_affichage].head(70))
    
    return df

def main():
    # Charger le modèle spaCy avec vecteurs Word2Vec
    nlp = spacy.load("en_core_web_md")

    # Nettoyer et préparer le DataFrame de logs
    df = clean("logs.csv")

    # Parcourir chaque log dans la colonne 'message'
    for text in df['message']:
        # Analyser chaque log avec spaCy. Cela crée un objet 'doc' contenant toutes les informations NLP.
        doc = nlp(text)

        # Afficher le texte du log que nous analysons
        print(f"\nTexte : {text}")

        # === Named Entity Recognition ===
        # Identifier et afficher les entités nommées (dates, IP, noms…)
        for ent in doc.ents:
            print(f" - Entité : {ent.text} | Type : {ent.label_}")

        # === Tokenisation ===
        print("\n=== [Tokenisation] ===")
        for token in doc:
            print(f"Token: {token.text}")

        # === Part-of-Speech Tagging ===
        print("\n=== [Part-of-Speech Tagging] ===")
        for token in doc:
            print(f"Token: {token.text} | POS: {token.pos_} | Lemma: {token.lemma_}")

        # === Dependency Parsing ===
        print("\n=== [Dependency Parsing] ===")
        for token in doc:
            print(f"Mot: {token.text} | Rôle: {token.dep_} | Attaché à: {token.head.text}")

        # === Word2Vec Embedding ===
        print("\n=== [Word2Vec Embedding] ===")
        if doc.vector_norm:  # Vérifie si des vecteurs sont disponibles
            print(f"Vecteur du document (taille {len(doc.vector)}):")
            print(doc.vector)
        else:
            print("Aucun vecteur disponible avec ce modèle pour le texte donné.")

        # Exemple : similarité entre les deux premiers tokens
        if len(doc) >= 2 and doc[0].has_vector and doc[1].has_vector:
            sim = doc[0].similarity(doc[1])  # Mesure de similarité
            print(f"\nSimilarité entre '{doc[0].text}' et '{doc[1].text}' : {sim:.3f}")
        else:
            print("Impossible de comparer des tokens : vecteurs non disponibles.")

def get_log_vectors(logs):
    # Fonction utilitaire pour obtenir les vecteurs de chaque log
    nlp = spacy.load("en_core_web_md")
    return [nlp(log).vector for log in logs]

if __name__ == "__main__":
    main()

