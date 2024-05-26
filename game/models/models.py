# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

logging.basicConfig(filename='/var/log/odoo/odoo-server.log.4', level=logging.DEBUG)


class Player(models.Model):
    _name = 'game.player'
    _description = 'Game Player'

    name = fields.Char(string="Name", required=True)
    reference_field = fields.Char(string="Reference Field", compute='_compute_reference_field')
    creation_date = fields.Datetime(string="Creation Date", readonly=True, compute='_compute_creation_date')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'This name already exists')]

    town_hall_level = fields.Selection([('1', 'T-1'), ('2', 'T-2'), ('3', 'T-3'), ('4', 'T-4'), ('5', 'T-5')],
                                       string="Town Hall Level", required=True, default='1')

    gold = fields.Integer(string="Gold", default=1000)
    mana = fields.Integer(string="Mana", default=1000)
    food = fields.Integer(string="Food", default=1000)
    troops = fields.Integer(string="Troops", default=0)

    buildings = fields.One2many('game.building', 'player_id', string="Buildings", ondelete='cascade')
    total_resources = fields.Float(string="Total Resources", compute='_compute_total_resources')

    battle_results = fields.Many2many('game.battle', string="Battle Results", compute='_compute_battle_results')

    @api.depends()
    def _compute_battle_results(self):
        for player in self:
            battles = self.env['game.battle'].search([
                '|',
                ('attacker_id', '=', player.id),
                ('defender_id', '=', player.id)
            ])
            player.battle_results = battles

    @api.depends('gold', 'mana', 'food')
    def _compute_total_resources(self):
        for player in self:
            player.total_resources = player.gold + player.mana + player.food

    @api.depends('create_date')
    def _compute_creation_date(self):
        for player in self:
            player.creation_date = player.create_date

    @api.depends('name')
    def _compute_reference_field(self):
        for player in self:
            if player.name:
                player.reference_field = player.name.upper()
            else:
                player.reference_field = "default".upper()

    @api.constrains('gold', 'mana', 'food')
    def _check_non_negative_resources(self):
        for player in self:
            if player.gold < 0 or player.mana < 0 or player.food < 0:
                raise ValidationError("Resources cannot be negative.")

    @api.constrains('troops')
    def _check_non_negative_troops(self):
        for player in self:
            if player.troops < 0:
                raise ValidationError("Troops cannot be negative.")

    @api.constrains('town_hall_level')
    def _check_town_hall_level_range(self):
        for player in self:
            if player.town_hall_level not in ['1', '2', '3', '4', '5']:
                raise ValidationError("Invalid town hall level.")

    def can_build_more_buildings(self):
        return True


class BuildingType(models.Model):
    _name = 'game.building.type'
    _description = 'Building Type'

    name = fields.Char(string="Name")
    gold_production = fields.Integer(string="Gold Production")
    mana_production = fields.Integer(string="Mana Production")
    food_production = fields.Integer(string="Food Production")
    troop_production = fields.Integer(string="Troop Production")

    icon = fields.Image(string="Icon", max_width=200, max_height=200)

    # Costos de construcción y mejora
    base_gold_cost = fields.Integer(string="Base Gold Cost", default=0)
    base_mana_cost = fields.Integer(string="Base Mana Cost", default=0)
    base_food_cost = fields.Integer(string="Base Food Cost", default=0)
    base_construction_time = fields.Integer(string="Base Construction Time", default=0)  # en minutos
    max_level = fields.Integer(string="Max Level", default=1)

    @property
    def gold_cost(self):
        return self.base_gold_cost

    @property
    def mana_cost(self):
        return self.base_mana_cost

    @property
    def food_cost(self):
        return self.base_food_cost

    @property
    def construction_time(self):
        return self.base_construction_time

    # Costos de mejora
    upgrade_gold_cost = fields.Integer(string="Upgrade Gold Cost", default=0)
    upgrade_mana_cost = fields.Integer(string="Upgrade Mana Cost", default=0)
    upgrade_food_cost = fields.Integer(string="Upgrade Food Cost", default=0)

    @api.constrains('base_gold_cost', 'base_mana_cost', 'base_food_cost', 'upgrade_gold_cost', 'upgrade_mana_cost',
                    'upgrade_food_cost')
    def _check_non_negative_costs(self):
        for building_type in self:
            if (building_type.base_gold_cost < 0 or building_type.base_mana_cost < 0 or building_type.base_food_cost < 0
                    or building_type.upgrade_gold_cost < 0 or building_type.upgrade_mana_cost < 0 or building_type.upgrade_food_cost < 0):
                raise ValidationError("Costs cannot be negative.")

    @api.constrains('base_construction_time')
    def _check_non_negative_construction_time(self):
        for building_type in self:
            if building_type.base_construction_time < 0:
                raise ValidationError("Construction time cannot be negative.")

    @api.constrains('max_level')
    def _check_max_level(self):
        for building_type in self:
            if building_type.max_level < 1:
                raise ValidationError("Max level must be greater than or equal to 1.")


class Building(models.Model):
    _name = 'game.building'
    _description = 'Building'

    name = fields.Char(string="Name", compute='_compute_name', store=True)
    player_id = fields.Many2one('game.player', string="Player", required=True, ondelete='cascade')
    player_name = fields.Char(string="Player Name", related='player_id.name', store=True)
    type_id = fields.Many2one('game.building.type', string="Building Type", required=True)
    level = fields.Integer(string="Level", default=1)
    is_constructed = fields.Boolean(string="Is Constructed", default=False)
    construction_progress = fields.Integer(string="Construction Progress", compute='_compute_construction_progress')
    remaining_construction_time = fields.Integer(string="Remaining Construction Time", default=0)
    construction_time = fields.Integer(string="Construction Time", default=0)
    construction_start_time = fields.Datetime(string="Construction Start Time")
    completion_date = fields.Datetime(string="Completion Date", compute='_compute_completion_date', store=True)
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Date(string='End Date')

    @api.depends('type_id')
    def _compute_name(self):
        for building in self:
            building.name = building.type_id.name

    @api.depends('level', 'construction_time', 'remaining_construction_time')
    def _compute_construction_progress(self):
        for building in self:
            if building.construction_time:
                total_construction_time = building.construction_time
                remaining_time = building.remaining_construction_time
                if remaining_time == 0:
                    building.construction_progress = 100  # Si el tiempo restante es 0, el progreso es 100%
                elif total_construction_time > 0:
                    building.construction_progress = (
                                                             total_construction_time - remaining_time) / total_construction_time * 100
                else:
                    building.construction_progress = 0
            else:
                building.construction_progress = 100

    @api.model
    def create(self, vals):
        building = super(Building, self).create(vals)
        building.construction_time = building.level * 60
        return building

    def action_construct(self):
        for building in self:
            if building.is_constructed:
                raise ValidationError("The building is already constructed.")
            building_type = building.type_id
            if not building.is_constructed:
                if building.player_id.gold >= building_type.base_gold_cost and \
                        building.player_id.mana >= building_type.base_mana_cost and \
                        building.player_id.food >= building_type.base_food_cost and \
                        building.player_id.can_build_more_buildings():
                    building.player_id.gold -= building_type.base_gold_cost
                    building.player_id.mana -= building_type.base_mana_cost
                    building.player_id.food -= building_type.base_food_cost
                    building.is_constructed = False
                    building.construction_start_time = fields.Datetime.now()
                    building.remaining_construction_time = building.construction_time
                    # Lanza el temporizador
                    self.env['ir.cron'].sudo().create({
                        'name': f"Construction Timer for {building.name}",
                        'model_id': self.env.ref('game.model_game_building').id,
                        'state': 'code',
                        'code': f"model.browse({building.id}).update_construction_state()",
                        'interval_number': 1,
                        'interval_type': 'minutes',
                        'numbercall': building.construction_time + 1,
                        'doall': False,
                        'active': True
                    })
                else:
                    raise ValidationError("Cannot upgrade because the player does not have enough resources.")

            else:
                raise ValidationError("Cannot construct a building that is already constructed.")

    def update_construction_state(self):
        for building in self:
            if building.remaining_construction_time == 0:
                building.is_constructed = True
                building.remaining_construction_time = 0
            else:
                building.remaining_construction_time -= 1

    def action_upgrade(self):
        for building in self:
            if not building.is_constructed:
                raise ValidationError("Cannot upgrade while construction is in progress.")
            building_type = building.type_id
            if building.level < building_type.max_level:
                if building.player_id.gold >= building_type.upgrade_gold_cost and \
                        building.player_id.mana >= building_type.upgrade_mana_cost and \
                        building.player_id.food >= building_type.upgrade_food_cost:
                    building.player_id.gold -= building_type.upgrade_gold_cost
                    building.player_id.mana -= building_type.upgrade_mana_cost
                    building.player_id.food -= building_type.upgrade_food_cost
                    building.level += 1
                    building.construction_time = building.level * 60
                    building.is_constructed = False
                    building.remaining_construction_time = building.construction_time
                    building.construction_start_time = fields.Datetime.now()
                    # Lanza el temporizador
                    self.env['ir.cron'].sudo().create({
                        'name': f"Upgrade Timer for {building.name}",
                        'model_id': self.env.ref('game.model_game_building').id,
                        'state': 'code',
                        'code': f"model.browse({building.id}).update_construction_state()",
                        'interval_number': 1,
                        'interval_type': 'minutes',
                        'numbercall': building.construction_time,
                        'doall': False,
                        'active': True
                    })
                else:
                    raise ValidationError("Cannot upgrade because the player does not have enough resources.")
            else:
                raise ValidationError("Cannot upgrade because it is already the maximum level.")

    @api.depends('construction_start_time', 'construction_time')
    def _compute_completion_date(self):
        for building in self:
            if building.construction_start_time and building.construction_time:
                start_time = fields.Datetime.from_string(building.construction_start_time)
                completion_time = start_time + timedelta(minutes=building.construction_time)
                building.completion_date = completion_time
            else:
                building.completion_date = False

    def generate_resources(self):
        for building in self.search([]):
            if building.is_constructed and building.type_id:
                # Calcula la cantidad de recursos que se generan por segundo
                gold_per_minute = building.type_id.gold_production
                mana_per_minute = building.type_id.mana_production
                food_per_minute = building.type_id.food_production
                troops_per_minute = building.type_id.troop_production
                # Asigna los recursos al jugador propietario del edificio
                building.player_id.gold += gold_per_minute
                building.player_id.mana += mana_per_minute
                building.player_id.food += food_per_minute
                building.player_id.troops += troops_per_minute

    def get_building_summaries(self):
        all_buildings = self.search([('is_constructed', '=', False)])
        buildings_sorted_by_level = all_buildings.sorted(key=lambda b: b.level)
        summaries = buildings_sorted_by_level.mapped(lambda b: {
            'name': b.name,
            'player_name': b.player_name,
            'level': b.level,
            'remaining_construction_time': b.remaining_construction_time
        })

        return summaries

    def load_building_summaries(self):
        self.env['game.building.summary'].search([]).unlink()
        summaries = self.get_building_summaries()
        for summary in summaries:
            self.env['game.building.summary'].create(summary)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Building Summaries',
            'res_model': 'game.building.summary',
            'view_mode': 'tree',
            'target': 'new',
        }


class BuildingSummary(models.TransientModel):
    _name = 'game.building.summary'
    _description = 'Building Summary'

    name = fields.Char(string="Name")
    player_name = fields.Char(string="Player Name")
    level = fields.Integer(string="Level")
    remaining_construction_time = fields.Integer(string="Remaining Construction Time")


class BattleSimulation(models.Model):
    _name = 'game.battle'
    _description = 'Battle Simulation'

    attacker_id = fields.Many2one('game.player', string="Attacker", required=True, ondelete='cascade')
    defender_id = fields.Many2one('game.player', string="Defender", required=True, ondelete='cascade')
    result = fields.Selection(
        [('attacker_win', 'Attacker Wins'), ('defender_win', 'Defender Wins'), ('draw', 'Draw')],
        string="Result")
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done')],
                             default='draft', string="State")
    progress = fields.Integer(string='Progress', default=0)
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    def action_initiate_battle(self):
        logging.info('Batalla iniciada')
        start_date = fields.Datetime.now()
        end_date = start_date + timedelta(minutes=3)
        self.write({
            'state': 'in_progress',
            'progress': 0,
            'start_date': start_date,
            'end_date': end_date
        })
        self.update_battles()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Battles',
            'res_model': 'game.battle',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    @api.model
    def complete_battle(self, battle_id):
        battle = self.browse(battle_id)
        if battle:
            battle.write({
                'state': 'done',
                'progress': 100
            })
            battle.simulate_battle()

    def simulate_battle(self):
        attacker_troops = self.attacker_id.troops
        defender_troops = self.defender_id.troops

        if attacker_troops > defender_troops:
            self.result = 'attacker_win'
            winner = self.attacker_id
            loser = self.defender_id
        elif attacker_troops < defender_troops:
            self.result = 'defender_win'
            winner = self.defender_id
            loser = self.attacker_id
        else:
            self.result = 'draw'
            return

        resources_loser = {'gold': loser.gold, 'mana': loser.mana, 'food': loser.food}
        loser_troops_lost = int(loser.troops * 0.5)
        loser_resources_lost = {resource: int(value * 0.25) for resource, value in resources_loser.items()}

        winner.write({
            'troops': winner.troops - loser_troops_lost,
            'gold': winner.gold + loser_resources_lost['gold'],
            'mana': winner.mana + loser_resources_lost['mana'],
            'food': winner.food + loser_resources_lost['food']
        })

        loser.write({
            'troops': loser.troops - loser_troops_lost,
            'gold': loser.gold - loser_resources_lost['gold'],
            'mana': loser.mana - loser_resources_lost['mana'],
            'food': loser.food - loser_resources_lost['food']
        })

    def update_battles(self):
        logging.info('El cron funciona')
        battles_in_progress = self.search([('state', '=', 'in_progress')])
        logging.info(battles_in_progress)
        for battle in battles_in_progress:
            logging.info(battle.end_date)
            if battle.end_date <= fields.Datetime.now():
                logging.info('La batalla finalizo')
                battle.complete_battle(battle.id)


class PlayerCreationWizard(models.TransientModel):
    _name = 'game.player.creation.wizard'
    _description = 'Player Creation Wizard'

    name = fields.Char(string="Player Name", required=True)
    town_hall_level = fields.Selection([
        ('1', 'T-1'), ('2', 'T-2'), ('3', 'T-3'), ('4', 'T-4'), ('5', 'T-5')],
        string="Town Hall Level", required=True, default='1')
    buildings = fields.Many2many('game.building.wizard', string="Buildings")

    state = fields.Selection([
        ('step1', 'Step 1'),
        ('step2', 'Step 2')],
        default='step1')

    @api.model
    def default_get(self, fields):
        res = super(PlayerCreationWizard, self).default_get(fields)
        if self.env.context.get('wizard_reopen'):
            res.update({
                'name': self.env.context.get('default_name'),
                'town_hall_level': self.env.context.get('default_town_hall_level'),
                'buildings': [(6, 0, self.env.context.get('default_buildings'))]
            })
        return res

    def action_next(self):
        if self.state == 'step1':
            self.state = 'step2'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Player Wizard',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': {
                'default_name': self.name,
                'default_town_hall_level': self.town_hall_level,
                'default_buildings': self.buildings.ids,
                'wizard_reopen': True
            }
        }

    def action_previous(self):
        if self.state == 'step2':
            self.state = 'step1'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Player Wizard',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': {
                'default_name': self.name,
                'default_town_hall_level': self.town_hall_level,
                'default_buildings': self.buildings.ids,
                'wizard_reopen': True
            }
        }

    def action_create_player(self):
        # Crea el jugador
        player = self.env['game.player'].create({
            'name': self.name,
            'town_hall_level': self.town_hall_level,
        })

        # Crea los edificios asociados al jugador pero no los construye
        # asi que no generan recursos hay que ir a los edificios y posteriormente construirlos
        for building_data in self.buildings:
            building = self.env['game.building'].create({
                'name': building_data.name,
                'type_id': building_data.type_id.id,
                'level': building_data.level,
                'player_id': player.id,
            })

            return {
                'type': 'ir.actions.act_window',
                'name': 'Players',
                'res_model': 'game.player',
                'view_mode': 'tree,form',
                'target': 'current',
            }


class BuildingWizard(models.TransientModel):
    _name = 'game.building.wizard'
    _description = 'Building Creation Wizard'

    name = fields.Char(string="Name", store=True, readonly=True)
    type_id = fields.Many2one('game.building.type', string="Building Type", required=True)
    level = fields.Integer(string="Level", default=1)

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            self.name = self.type_id.name


class BattleWizard(models.TransientModel):
    _name = 'game.battle_wizard'
    _description = 'Battle Wizard'

    attacker_id = fields.Many2one('game.player', string="Attacker", required=True, ondelete='cascade')
    defender_id = fields.Many2one('game.player', string="Defender", required=True, ondelete='cascade')
    result = fields.Selection([('attacker_win', 'Attacker Wins'), ('defender_win', 'Defender Wins'), ('draw', 'Draw')],
                              string="Result", readonly=True)
    state = fields.Selection([
        ('step1', 'Step 1'),
        ('step2', 'Step 2')],
        default='step1')

    @api.onchange('attacker_id', 'defender_id')
    def _onchange_players(self):
        if self.attacker_id and self.defender_id:
            self.result = 'draw' if self.attacker_id.troops == self.defender_id.troops else 'attacker_win' if self.attacker_id.troops > self.defender_id.troops else 'defender_win'

    def action_next(self):
        if self.state == 'step1':
            self.state = 'step2'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Battle Wizard',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def action_previous(self):
        if self.state == 'step2':
            self.state = 'step1'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Battle Wizard',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def action_initiate_battle(self):
        battle = self.env['game.battle'].create({
            'attacker_id': self.attacker_id.id,
            'defender_id': self.defender_id.id,
            'result': self.result,
            'state': 'in_progress',
            'progress': 0,
            'start_date': fields.Datetime.now(),
            'end_date': (fields.Datetime.now() + timedelta(minutes=3))
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Battles',
            'res_model': 'game.battle',
            'view_mode': 'tree,form',
            'target': 'current',
        }
