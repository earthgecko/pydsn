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
    timezoneoffset = BigIntegerField(db_column='timeZoneOffset', null=True)

    class Meta:
        db_table = 'configSite'

class ConfigDish(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configsiteid = IntegerField(db_column='configSiteID') #ForeignKeyField(ConfigSite)
    friendlyname = TextField(db_column='friendlyName')
    name = CharField()
    type = CharField()

    class Meta:
        db_table = 'configDish'

class ConfigSpacecraft(BaseModel):
    encoding = CharField(null=True)
    id = PrimaryKeyField(db_column='ID')
    flags = CharField()
    friendlyname = TextField(db_column='friendlyName')
    lastid = IntegerField(db_column='lastID', null=True, unique=True)
    name = CharField(unique=True)

    class Meta:
        db_table = 'configSpacecraft'

class ConfigState(BaseModel):
    decoder1 = CharField(null=True)
    decoder2 = CharField(null=True)
    encoding = CharField(null=True)
    flags = CharField()
    id = PrimaryKeyField(db_column='ID')
    name = CharField(db_column='state', unique=True)
    updown = CharField(db_column='upDown')
    signaltype = CharField(db_column='signalType')
    task = CharField(null=True)
    valuetype = CharField(db_column='valueType')

    class Meta:
        db_table = 'configState'

class DataEvent(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    time = BigIntegerField()

    class Meta:
        db_table = 'dataEvent'

class DataDish(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configdishid = IntegerField(db_column='configDishID') #ForeignKeyField(ConfigDish)
    createdtime = BigIntegerField(db_column='createdTime')
    eventid = IntegerField(db_column='eventID')
    flags = CharField()
    updatedtime = BigIntegerField(db_column='updatedTime')
    targetspacecraft1 = IntegerField(db_column='targetSpacecraft1', null=True)
    targetspacecraft2 = IntegerField(db_column='targetSpacecraft2', null=True)
    targetspacecraft3 = IntegerField(db_column='targetSpacecraft3', null=True)

    class Meta:
        db_table = 'dataDish'

class DataDishPos(BaseModel):
    azimuthangle = FloatField(db_column='azimuthAngle')
    configdishid = IntegerField(db_column='configDishID') #ForeignKeyField(ConfigDish)
    elevationangle = FloatField(db_column='elevationAngle')
    eventid = IntegerField(db_column='eventID')
    windspeed = FloatField(db_column='windSpeed')

    class Meta:
        db_table = 'dataDishPos'

class DataSignal(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configdishid = IntegerField(db_column='configDishID') #ForeignKeyField(ConfigDish)
    configspacecraftid = IntegerField(db_column='configSpacecraftID') #ForeignKeyField(ConfigSpacecraft)
    datadishid = IntegerField(db_column='dataDishID') #ForeignKeyField(DataDish)
    eventid = IntegerField(db_column='eventID')
    flags = CharField()
    stateid = IntegerField(db_column='stateID') #ForeignKeyField(ConfigState)
    updown = CharField(db_column='upDown')

    class Meta:
        db_table = 'dataSignal'

class DataSignalDet(BaseModel):
    datarate = FloatField(db_column='dataRate', null=True)
    datasignalid = IntegerField(db_column='dataSignalID') #ForeignKeyField(DataSignal)
    eventid = IntegerField(db_column='eventID')
    frequency = FloatField(null=True)
    power = FloatField(null=True)

    class Meta:
        db_table = 'dataSignalDet'

class DataTarget(BaseModel):
    id = PrimaryKeyField(db_column='ID')
    configdishid = IntegerField(db_column='configDishID') #ForeignKeyField(ConfigDish)
    configspacecraftid = IntegerField(db_column='configSpacecraftID') #ForeignKeyField(ConfigSpacecraft)
    downlegrange = FloatField(db_column='downlegRange')
    eventid = IntegerField(db_column='eventID')
    rtlt = FloatField()
    uplegrange = FloatField(db_column='uplegRange')

    class Meta:
        db_table = 'dataTarget'
