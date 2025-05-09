#!/bin/bash

# Fichier CSV source
FILE="/data/opensearch/dvf-data/full-2023.csv"

# Index cible dans OpenSearch
INDEX="dvf-f"

# Supprimer l'index s'il existe
curl -XDELETE "https://os01:9200/$INDEX?pretty" -u 'admin:admin' -k

# Importer via Logstash
cat "$FILE" | /usr/share/logstash/bin/logstash \
  -f /data/opensearch/dvf-opensearch.conf \
  --pipeline.batch.size 1000 \
  --pipeline.batch.delay 5 \
  --path.data /tmp/dvf-$(date +%s)
