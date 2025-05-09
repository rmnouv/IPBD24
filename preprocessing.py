from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import sys

# Check arguments
if len(sys.argv) != 3:
    print("Usage: spark-submit ipbd_projet.py <input_path> <output_path>")
    sys.exit(1)

input_path = sys.argv[1]
output_path = sys.argv[2]

# Start Spark session
spark = SparkSession.builder \
    .appName("IPBD Project") \
    .getOrCreate()

# Read CSV using PySpark
df = spark.read.option("header", "true").option("sep", ",").csv(input_path)

# Drop rows with nulls in critical columns
df = df.dropna(subset=["valeur_fonciere", "longitude", "latitude"])

# Cast string-like columns explicitly
for col_name, dtype in df.dtypes:
    if dtype == "string":
        df = df.withColumn(col_name, col(col_name).cast("string"))

# Write as a CSV file
df.coalesce(1).write.mode("overwrite").option("header", "true").csv(output_path)

print("Successfully exported to CSV!")