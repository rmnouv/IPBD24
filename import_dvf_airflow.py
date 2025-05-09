# -*- coding: utf-8 -*-
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator
from datetime import datetime
import json

# Fichier CSV en entrée
CSV_FILE = "/shared/dvf-data/full-2024.csv"
LOGSTASH_CONF = "/shared/dvf-data/dvf-opensearch-2024.conf"
TEMPLATE_FILE = "/shared/dvf-data/dvf-template-opensearch-2024.json"


def create_template_file():
    content = {
        "index_patterns": ["dvf-2024"],
        "settings": {
            "index.number_of_shards": 1,
            "index.number_of_replicas": 0,
            "index.analysis": {
                "analyzer": {
                    "dvf_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    },
                    "dvf_street_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        },
        "mappings": {
            "_source": {"enabled": True},
            "properties": {
                "id_mutation": {"type": "keyword"},
                "date_mutation": {"type": "date", "format": "yyyy-MM-dd"},
                "valeur_fonciere": {"type": "float"},
                "surface_reelle_bati": {"type": "float"},
                "surface_terrain": {"type": "float"},
                "location": {"type": "geo_point"},
                "code_postal": {"type": "keyword"},
                "code_commune": {"type": "keyword"},
                "nom_commune": {
                    "type": "text",
                    "analyzer": "dvf_analyzer",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "code_type_local": {"type": "keyword"},
                "type_local": {"type": "keyword"},
                "nombre_pieces_principales": {"type": "integer"}
            }
        }
    }
    with open(TEMPLATE_FILE, "w") as f:
        json.dump(content, f, indent=2)


def create_logstash_conf():
    conf = f"""
input {{
  stdin {{}}
}}

filter {{
  csv {{
    separator => ","
    columns => ["id_mutation", "date_mutation", "numero_disposition", "nature_mutation", "valeur_fonciere", "adresse_numero", "adresse_suffixe", "adresse_code_voie", "adresse_nom_voie", "code_postal", "code_commune", "nom_commune", "ancien_code_commune", "ancien_nom_commune", "code_departement", "id_parcelle", "ancien_id_parcelle", "numero_volume", "lot_1_numero", "lot_1_surface_carrez", "lot_2_numero", "lot_2_surface_carrez", "lot_3_numero", "lot_3_surface_carrez", "lot_4_numero", "lot_4_surface_carrez", "lot_5_numero", "lot_5_surface_carrez", "nombre_lots", "code_type_local", "type_local", "surface_reelle_bati", "nombre_pieces_principales", "code_nature_culture", "nature_culture", "code_nature_culture_speciale", "nature_culture_speciale", "surface_terrain", "longitude", "latitude"]
    skip_empty_columns => true
  }}
  if [id_mutation] == "id_mutation" {{ drop {{ }} }}
  mutate {{
    convert => {{ "valeur_fonciere" => "float" "surface_reelle_bati" => "float" "surface_terrain" => "float" "longitude" => "float" "latitude" => "float" }}
    rename => {{ "longitude" => "[location][lon]" "latitude" => "[location][lat]" }}
  }}
}}

output {{
  opensearch {{
    hosts => ["https://os01:9200", "https://os02:9200", "https://os03:9200"]
    auth_type => {{ type => 'basic' user => 'admin' password => 'admin' }}
    cacert => "/usr/share/logstash/config/certificates/ca/ca.pem"
    ssl_certificate_verification => false
    template => "{TEMPLATE_FILE}"
    template_overwrite => true
    template_name => "dvf-2024"
    index => "dvf-2024"
    document_id => "%{{[id_mutation]}}"
  }}
}}
"""
    with open(LOGSTASH_CONF, "w") as f:
        f.write(conf)


defaul_args = {
    'start_date': datetime(2025, 5, 10)
}

dag = DAG(
    dag_id='import_dvf_airflow',
    schedule=None,
    catchup=False,
    default_args=defaul_args,
    description='Importation automatique des donnees DVF 2024 dans OpenSearch'
)

create_template = PythonOperator(
    task_id='create_opensearch_template',
    python_callable=create_template_file,
    dag=dag
)

create_conf = PythonOperator(
    task_id='create_logstash_conf',
    python_callable=create_logstash_conf,
    dag=dag
)

run_logstash = BashOperator(
    task_id='run_logstash_import',
    bash_command=f"cat {CSV_FILE} | /usr/share/logstash/bin/logstash -f {LOGSTASH_CONF} --path.data /tmp/dvf-import-$(date +%s)",
    dag=dag
)

create_template >> create_conf >> run_logstash
