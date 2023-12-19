# -*- coding: utf-8 -*-

from odoo import models, fields, api


class player(models.Model):
    _name = 'game.player'
    _description = 'Game Player'

    name = fields.Char(required=True)
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Este nombre ya existe')]

    town_hall_level = fields.Selection([('1', 'T-1'), ('2', 'T-2'), ('3', 'T-3'), ('4', 'T-4'), ('5', 'T-5')],
                                       required=True, default='1')
    mine_level = fields.Integer()
    mana_level = fields.Integer()
    orchard_level = fields.Integer()
    warehouse_level = fields.Integer()
    barracks_level = fields.Integer()

    gold = fields.Float(default=1000)
    mana = fields.Float(default=1000)
    food = fields.Float(default=1000)


class building_type(models.Model):
    _name = 'game.building.type'
    _description = 'Building Type'

    name = fields.Char()
    gold_production = fields.Integer()
    mana_production = fields.Integer()
    food_production = fields.Integer()
    troop_production = fields.Integer()

    icon = fields.Image(max_width=200, max_height=200)


class building(models.Model):
    _name = 'game.building'
    _description = 'Building'

    name = fields.Char(compute='_get_name')
    type = fields.Many2one('game.building.type', required=True)
    player_id = fields.Many2one('game.player', required=True)
    level = fields.Integer(defaul=1)
    food_production = fields.Float(compute='_get_productions')
    soldiers_production = fields.Float(compute='_get_productions')
    gold_production = fields.Float(compute='_get_productions')
    metal_production = fields.Float(compute='_get_productions')
