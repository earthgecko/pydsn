# coding=utf-8
from peewee import *

database = MySQLDatabase(None)

class BaseModel(Model):
    class Meta:
        database = database

class ConfigSite(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    friendlyname = TextField(db_column='friendlyName')
    latitude = FloatField()
    longitude = FloatField()
    name = CharField(unique=True)

    class Meta:
        db_table = 'configSite'

class ConfigDish(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configsiteid = ForeignKeyField(ConfigSite, db_column='configSiteID')
    friendlyname = TextField(db_column='friendlyName')
    name = CharField()
    type = CharField()

    class Meta:
        db_table = 'configDish'

class ConfigSpacecraft(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    friendlyname = TextField(db_column='friendlyName')
    lastid = IntegerField(db_column='lastID', null=True, unique=True)
    name = CharField(unique=True)

    class Meta:
        db_table = 'configSpacecraft'

class DataDish(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    azimuthangle = FloatField(db_column='azimuthAngle')
    configdishid = ForeignKeyField(ConfigDish, db_column='configDishID')
    created = DateTimeField()
    elevationangle = FloatField(db_column='elevationAngle')
    flags = CharField()
    time = BigIntegerField()
    updated = DateTimeField()
    windspeed = FloatField(db_column='windSpeed')

    class Meta:
        db_table = 'dataDish'

class DataSignal(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configdishid = ForeignKeyField(ConfigDish, db_column='configDishID')
    configspacecraftid = ForeignKeyField(ConfigSpacecraft, db_column='configSpacecraftID', null=True)
    datarate = FloatField(db_column='dataRate', null=True)
    decoder1 = CharField(null=True)
    decoder2 = CharField(null=True)
    encoding = CharField(null=True)
    flags = CharField()
    frequency = FloatField(null=True)
    power = FloatField(null=True)
    seq = IntegerField()
    signaltype = CharField(db_column='signalType')
    signaltypedebug = CharField(db_column='signalTypeDebug', null=True)
    time = BigIntegerField()
    updown = CharField(db_column='upDown')

    class Meta:
        db_table = 'dataSignal'

class DataSite(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configsiteid = ForeignKeyField(ConfigSite, db_column='configSiteID')
    time = BigIntegerField()
    timeutc = BigIntegerField(db_column='timeUTC')
    timezoneoffset = BigIntegerField(db_column='timeZoneOffset')

    class Meta:
        db_table = 'dataSite'

class DataTarget(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configdishid = ForeignKeyField(ConfigDish, db_column='configDishID')
    configspacecraftid = ForeignKeyField(ConfigSpacecraft, db_column='configSpacecraftID')
    downlegrange = FloatField(db_column='downlegRange')
    rtlt = FloatField()
    time = BigIntegerField()
    uplegrange = FloatField(db_column='uplegRange')

    class Meta:
        db_table = 'dataTarget'
