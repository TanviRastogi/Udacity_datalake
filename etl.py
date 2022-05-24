import configparser
from datetime import datetime
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.functions import year, month, dayofmonth, hour, weekofyear, date_format


config = configparser.ConfigParser()
config.read('dl.cfg')

os.environ['AWS_ACCESS_KEY_ID']=config['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY']=config['AWS_SECRET_ACCESS_KEY']


def create_spark_session():
    spark = SparkSession \
        .builder \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:2.7.0") \
        .getOrCreate()
    return spark


def process_song_data(spark, input_data, output_data):
    # get filepath to song data file
    song_data =  os.path.join(input_data, 'song_data/*/*/*/*.json')
   
    # read song data file
    df = spark.read.json(song_data)

    # extract columns to create songs table
    songs_table = df.select('song_id', 'title', 'artist_id','year', 'duration').dropduplicates() 
    
    
    # write songs table to parquet files partitioned by year and artist
    songs_table.write.partitionBy("year", "artist").parquet(output_data+'songs_table/')

    # extract columns to create artists table
    artists_table = df.select('artist_id', col('artist_name').alias('name'), col('artist_location').alias('location'),col('artist_latitude').alias('latitude'),                           col('artist_longitude').alias('longitude')).distinct()
    
    # write artists table to parquet files
    artists_table.write.parquet(output_data+'artists_table/')


def process_log_data(spark, input_data, output_data):
    # get filepath to log data file
    log_data = os.path.join(input_data, 'log_data/*/*/*.json')

    # read log data file
    df = spark.read.json(log_data)
    
    # filter by actions for song plays
    df = df.filter(df.page == 'NextSong')

    # extract columns for users table    
    artists_table = df.select(col('userId').alias('user_id'),col('firstName').alias('first_name'), col('lastName').alias('last_name'), 'gender', 'level').distinct()
    
    
    # write users table to parquet files
    artists_table.write.parquet(output_data+'users_table/')

    # create timestamp column from original timestamp column
    get_timestamp = udf(lambda x: str(datetime.fromtimestamp(int(x))))
    df = df.withColumn("timestamp", get_timestamp(df.ts))
    
    # create datetime column from original timestamp column
    get_datetime = udf(lambda x: str(datetime.fromtimestamp(int(x) / 1000)))
    df = df.withColumn('datetime', get_datetime(df.ts))
    
    # extract columns to create time table
    time_table = df.select('datetime') \
    .withColumn('start_time', df.datetime) \
    .withColumn('hour', hour('datetime')) \
    .withColumn('day', dayofmonth('datetime')) \
    .withColumn('week', weekofyear('datetime')) \
    .withColumn('month', month('datetime')) \
    .withColumn('year', year('datetime')) \
    .withColumn('weekday', dayofweek('datetime')) \
    .dropDuplicates()
    
    # write time table to parquet files partitioned by year and month
    time_table.write.partitionBy('year', 'month').parquet(output_data + 'time/')

    # read in song data to use for songplays table
    song_df =spark.read.parquet(output_data + 'songs_table/')

    # extract columns from joined song and log datasets to create songplays table 
    songplays_table = df.join(song_df, (song_df.title == df.song) & (song_df.duration == df.length))
    songplays_table = songplays_table.withColumn('songplay_id', monotonically_increasing_id())
    songplays_table = songplays_table.select('songplay_id', col('timestamp').alias('start_time'),col('userId').alias('user_id'), 'level','song_id', 
                                             '  artist_id',col('sessionId').alias('session_id'),'location',col('userAgent').alias('user_agent'))

    # write songplays table to parquet files partitioned by year and month
    songplays_table.withColumn('year',year('start_time')).withColumn('month',month('start_time')).write.partitionBy('year','month').parquet(output_data+'songplay/')


def main():
    spark = create_spark_session()
    input_data = "s3a://udacity-dend/"
    output_data = "s3a://udacity-dend/tanvi/"
    
    process_song_data(spark, input_data, output_data)    
    process_log_data(spark, input_data, output_data)


if __name__ == "__main__":
    main()
