# -*- coding: utf-8 -*-

from flask import render_template, Response

import conf
from pyldapi import Renderer, Profile
from rdflib import Graph, URIRef, RDF, Namespace, Literal, BNode
from rdflib.namespace import XSD, SKOS   #imported for 'export_rdf' function

from .gazetteer import GAZETTEERS, NAME_AUTHORITIES
from .dggs_in_line import get_cells_in_json_and_return_in_json

# for DGGSC:C zone attribution
import requests
import ast
DGGS_API_URI = "http://ec2-54-206-28-241.ap-southeast-2.compute.amazonaws.com/api/search/"
# test_DGGS_API_URI = "https://dggs.loci.cat/api/search/"
DGGS_uri = 'http://ec2-52-63-73-113.ap-southeast-2.compute.amazonaws.com/AusPIX-DGGS-dataset/ausPIX/'

from rhealpixdggs import dggs
rdggs = dggs.RHEALPixDGGS()

# TABLE_NAME = 'AEIP_SA1join84'
TABLE_NAME = 'AEIP_SA1_84withResdensityv11'
NAME_FIELD = 'SA1_MAIN16'


class SA1_LOC_INFO(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/power/',
                'Power Line View',
                'This view is for power line delivered by the power line dataset'
                ' in accordance with the Power Line Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_LOC_INFO, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "SA2_MAIN16",
                   "SA2_NAME16",
                   "SA3_CODE16",                   
                   "SA3_NAME16",
                   "SA4_CODE16",
                   "SA4_NAME16",
                   "GCC_CODE16",
                   "GCC_NAME16",
                   "STE_CODE16",
                   "STE_NAME16",
                   "SA1SQKM16",
                   "aeip_LGA_WITHIN_AOI",
                   "aeip_LOCALITIES_WITHIN_AOI",
                   ST_AsEWKT(geom) As geom_wkt,
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/sa1/',
            'label': 'SA1 AEIP Location Information',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.thisFeature = []
        self.featureCords = []

        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.SA2_CODE = str(row[1])
            self.SA2_name = row[2]
            self.SA3_CODE = str(row[3])
            self.SA3_name = row[4]
            self.SA4_CODE = str(row[5])
            self.SA4_name = row[6]
            self.GCC_CODE = str(row[7])
            self.GCC_name = row[8]
            self.STE_CODE = str(row[9])
            self.STE_name = row[10]
            self.area_sqkm = row[11]
            self.LGA = row[12]
            self.Localities = row[13]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.wkt = row[-2]
            self.geometry_type = self.geom['type']

            # import pdb
            # pdb.set_trace()

            # using the web API to find the DGGS cells for the geojson
            dggs_api_param = {
                'resolution': 9,
                "dggs_as_polygon": True
            }

            geo_json = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": self.geom
                    }
                ]
            }

            # self.listOfCells = get_cells_in_json_and_return_in_json(geo_json, dggs_api_param['resolution'],
            #                                                         dggs_api_param['dggs_as_polygon'])['dggs_cells']

            try:
                res = requests.post('{}find_dggs_by_geojson'.format(DGGS_API_URI), params=dggs_api_param, json=geo_json)
                self.listOfCells = res.json()['dggs_cells']
            except:
                self.listOfCells = get_cells_in_json_and_return_in_json(geo_json, dggs_api_param['resolution'],
                                                                    dggs_api_param['dggs_as_polygon'])['dggs_cells']

            for cell in self.listOfCells:
                self.thisFeature.append({'label': str(cell),
                                      'uri': '{}{}'.format(DGGS_uri, str(cell))})


    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)


    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'sa1_loc_info.html'
        return Response(        # Response is a Flask class imported at the top of this script
            render_template(     # render_template is also a Flask module
                html_page,   # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                SA2_code=self.SA2_CODE,
                SA2_name=self.SA2_name,
                SA3_code=self.SA3_CODE,
                SA3_name=self.SA3_name,
                SA4_code=self.SA4_CODE,
                SA4_name=self.SA4_name,
                GCC_code=self.GCC_CODE,
                GCC_name=self.GCC_name,
                STE_code=self.STE_CODE,
                STE_name=self.STE_name,
                area_sqkm=self.area_sqkm,
                lga=self.LGA,
                localities=self.Localities,
                ausPIX_DGGS = self.thisFeature,
                wkt=self.wkt
            ),
            status=200,
            mimetype='text/html'
        )



    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''


    def export_rdf(self, model_view='SA1_AEIP'):
        g = Graph()  # make instance of a RDF graph

        # namespace declarations
        dcterms = Namespace('http://purl.org/dc/terms/')  # already imported
        g.bind('dcterms', dcterms)
        geo = Namespace('http://www.opengis.net/ont/geosparql#')
        g.bind('geo', geo)
        owl = Namespace('http://www.w3.org/2002/07/owl#')
        g.bind('owl', owl)
        rdfs = Namespace('http://www.w3.org/2000/01/rdf-schema#')
        g.bind('rdfs', rdfs)
        sf = Namespace('http://www.opengis.net/ont/sf#')
        g.bind('sf', sf)
        skos = Namespace('https://www.w3.org/2009/08/skos-reference/skos.html')

        geox = Namespace('http://linked.data.gov.au/def/geox#')
        g.bind('geox', geox)
        g.bind('xsd', XSD)

        core = Namespace('http://linked.data.gov.au/def/core#')
        g.bind('core', core)
        net = Namespace('http://linked.data.gov.au/def/net#')
        g.bind('net', net)

        auspix = URIRef('http://ec2-52-63-73-113.ap-southeast-2.compute.amazonaws.com/AusPIX-DGGS-dataset/')
        g.bind('auspix', auspix)

        ptype = Namespace('http://pid.geoscience.gov.au/def/voc/ga/PlaceType/')
        g.bind('ptype', ptype)

        # specific to powerline datasdet
        pline_ds = Namespace('http://linked.data.gov.au/dataset/powerlines/')
        g.bind('pline_ds', pline_ds)

        # made the cell ID the subject of the triples
        pline = Namespace('http://linked.data.gov.au/def/powerlines/')
        g.bind('pline', pline)

        # build the graphs
        power_line = URIRef('{}{}'.format(pline_ds, self.id))
        g.add((power_line, RDF.type, URIRef(pline + 'Powerline')))
        g.add((power_line, dcterms.identifier, Literal(self.id, datatype=pline.ID)))
        # g.add((power_line, pline.operator, Literal(str(self.operator), datatype=dcterms.Agent)))
        # g.add((power_line, pline.owner, Literal(str(self.owner), datatype=dcterms.Agent)))
        g.add((power_line, pline.description, Literal(str(self.descripton))))
        g.add((power_line, pline.lineclass, Literal(str(self.lineclass))))
        g.add((power_line, pline.capacityKV, Literal(str(self.capacitykv))))
        g.add((power_line, pline.state, Literal(str(self.state))))


        g.add((power_line, core.name, Literal(self.hasName['value'], lang='en-AU')))
        g.add((power_line, core.attriuteSource, Literal(str(self.attributesource))))
        # g.add((power_line, core.custodianAgency, Literal(str(self.custodianagency), datatype=SKOS.Concept)))
        # g.add((power_line, core.custodianLicensing, Literal(str(self.custodianlicensing), datatype=dcterms.LicenseDocument)))
        g.add((power_line, core.featureSource, Literal(str(self.featuresource))))
        g.add((power_line, core.featureType, URIRef(ptype + self.featuretype)))
        g.add((power_line, core.operationalStatus, Literal(str(self.operationalstatus), datatype=SKOS.Concept)))
        # g.add((power_line, core.sourceJurisdiction, Literal(str(self.sourcejurisdication), datatype=SKOS.Concept)))
        g.add((power_line, core.attriuteDate, Literal(str(self.attributedate), datatype=XSD.dateTime)))
        g.add((power_line, core.featureDate, Literal(str(self.featuredate), datatype=XSD.dateTime)))
        # g.add((power_line, core.loadingDate, Literal(str(self.loadingdate), datatype=XSD.dateTime)))
        g.add((power_line, core.planimetricAccuracy, Literal(str(self.planimetricaccuracy), datatype=core.Measure)))
        # g.add((power_line, core.sourceUFI, Literal(str(self.sourceUFI))))
        # g.add((power_line, core.verticalAccuracy, Literal(str(self.verticalaccuracy), datatype=core.Measure)))
        g.add((power_line, core.spatialConfidence, Literal(str(self.spatialconfidence))))


        pline_wkt = BNode()
        g.add((pline_wkt, RDF.type, URIRef(sf + self.geometry_type)))
        g.add((pline_wkt, geo.asWKT, Literal(self.wkt, datatype=geo.wktLiteral)))
        g.add((power_line, geo.hasGeometry, pline_wkt))

        pline_dggs = BNode()
        g.add((pline_dggs, RDF.type, URIRef(geo + 'Geometry')))
        g.add((pline_dggs, geox.asDGGS, Literal(self._generate_dggs(), datatype=geox.dggsLiteral)))
        g.add((power_line, geo.hasGeometry, pline_dggs))



        if self.mediatype == 'text/turtle':
            return Response(
                g.serialize(format='turtle'),
                mimetype = 'text/turtle'
            )
        elif self.mediatype == 'application/rdf+xml':
            return Response(
                g.serialize(format='application/rdf+xml'),
                mimetype = 'application/rdf+xml'
            )
        else: # JSON-LD
            return Response(
                g.serialize(format='json-ld'),
                mimetype = 'application/ld+json'
            )


class SA1_BULD_EXPO(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/power/',
                'Power Line View',
                'This view is for power line delivered by the power line dataset'
                ' in accordance with the Power Line Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_BULD_EXPO, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_POPULATION",
                   "aeip_DWELLINGS",
                   "aeip_BUILDINGS",
                   "aeip_PRE_1980_CONSTRUCTION_COUNT",
                   "aeip_PRE_1990_PROBABLE_ASBESTOS",
                   "aeip_RESIDENTIAL_RECONSTRUCTION_VALUE",
                   "aeip_RESIDENTIAL_CONTENTS_VALUE", 
                   "aeip_COMMERCIAL_BUILDING_COUNT",
                   "aeip_COMMERCIAL_RECONSTRUCTION_VALUE",
                   "aeip_INDUSTRIAL_BUILDING_COUNT",
                   "aeip_INDUSTRIAL_RECONSTRUCTION_VALUE",
                   "residensity1km_v11_mean",                            
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/sa1/',
            'label': 'SA1 AEIP Building Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.population = str(row[1])
            self.dwellings = row[2]
            self.buildings = str(row[3])
            self.pre_1980_construction_count = row[4]
            self.pre_1990_probable_asbestos = str(row[5])
            self.residential_reconstruction_value = row[6]
            self.residential_contents_value = str(row[7])
            self.commercial_building_count = row[8]
            self.commercial_reconstruction_value = str(row[9])
            self.industrial_building_count = row[10]
            self.industrial_reconstruction_value = row[11]
            self.residensity = row[12]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'building_exposure.html'
        return Response(        # Response is a Flask class imported at the top of this script
            render_template(     # render_template is also a Flask module
                html_page,   # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                population=self.population,
                dwellings=self.dwellings,
                buildings=self.buildings,
                pre_1980_construction_count=self.pre_1980_construction_count,
                pre_1990_probable_asbestos=self.pre_1990_probable_asbestos,
                residential_reconstruction_value=self.residential_reconstruction_value,
                residential_contents_value=self.residential_contents_value,
                commercial_building_count=self.commercial_building_count,
                commercial_reconstruction_value=self.commercial_reconstruction_value,
                industrial_building_count=self.industrial_building_count,
                industrial_reconstruction_value=self.industrial_reconstruction_value,
                residensity=self.residensity
            ),
            status=200,
            mimetype='text/html'
        )


    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)


    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''



class SA1_SEIFA(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 SEIFA View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the SEIFA Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_SEIFA, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_SEIFA_DECILE_SCORE_10",
                   "aeip_SEIFA_DECILE_SCORE_9",
                   "aeip_SEIFA_DECILE_SCORE_8",
                   "aeip_SEIFA_DECILE_SCORE_7",
                   "aeip_SEIFA_DECILE_SCORE_6",
                   "aeip_SEIFA_DECILE_SCORE_5",
                   "aeip_SEIFA_DECILE_SCORE_4", 
                   "aeip_SEIFA_DECILE_SCORE_3",
                   "aeip_SEIFA_DECILE_SCORE_2",
                   "aeip_SEIFA_DECILE_SCORE_1",
                   "aeip_WITHOUT_SEIFA_SCORE",                       
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 AEIP SEIFA Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.seifa_decile_score_10 = str(row[1])
            self.seifa_decile_score_9 = row[2]
            self.seifa_decile_score_8 = str(row[3])
            self.seifa_decile_score_7 = row[4]
            self.seifa_decile_score_6 = str(row[5])
            self.seifa_decile_score_5 = row[6]
            self.seifa_decile_score_4 = str(row[7])
            self.seifa_decile_score_3 = row[8]
            self.seifa_decile_score_2 = str(row[9])
            self.seifa_decile_score_1 = row[10]
            self.without_seifa_score = row[11]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'seifa.html'
        return Response(        # Response is a Flask class imported at the top of this script
            render_template(     # render_template is also a Flask module
                html_page,   # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                seifa_decile_score_10=self.seifa_decile_score_10,
                seifa_decile_score_9=self.seifa_decile_score_9,
                seifa_decile_score_8=self.seifa_decile_score_8,
                seifa_decile_score_7=self.seifa_decile_score_7,
                seifa_decile_score_6=self.seifa_decile_score_6,
                seifa_decile_score_5=self.seifa_decile_score_5,
                seifa_decile_score_4=self.seifa_decile_score_4,
                seifa_decile_score_3=self.seifa_decile_score_3,
                seifa_decile_score_2=self.seifa_decile_score_2,
                seifa_decile_score_1=self.seifa_decile_score_1,
                without_seifa_score=self.without_seifa_score
            ),
            status=200,
            mimetype='text/html'
        )


    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)


    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''


class SA1_DEMO(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Demographic Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Demographic Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_DEMO, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
           SELECT
               "SA1_MAIN16",
               "aeip_ALL_AGED_65_AND_OVER",
               "aeip_INCLUDES_PERSONS_AGED_14_YEARS_AND_UNDER",
               "aeip_INCLUDES_AN_INDIGENOUS_PERSON",
               "aeip_ARE_A_SINGLE_PARENT_HOUSEHOLD",
               "aeip_ARE_IN_NEED_OF_ASSISTANCE_FOR_SELF_CARE_ACTIVITIES",
               "aeip_INCLUDE_PERSONS_NOT_PROFICIENT_IN_ENGLISH",
               "aeip_DO_NOT_HAVE_ACCESS_TO_A_MOTOR_VEHICLE",
               "aeip_NO_ONE_HAS_COMPLETED_YEAR_12_OR_HIGHER",
               "aeip_MOVED_TO_THE_REGION_IN_THE_LAST_1_YEAR",
               "aeip_MOVED_TO_THE_REGION_IN_THE_LAST_5_YEARS",
               "aeip_TOP_5_EMPLOYING_INDUSTRIES",                 
               ST_AsGeoJSON(geom) As geom
           FROM "{}"
           WHERE "id" = '{}'
       '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 AEIP Demographic Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.all_aged_65_and_over = row[1]
            self.includes_persons_aged_14_years_and_under = row[2]
            self.includes_an_indigenous_person = row[3]
            self.are_a_single_parent_household = row[4]
            self.are_in_need_of_assistance_for_self_care_activites = row[5]
            self.include_persons_not_proficient_in_english = row[6]
            self.do_not_have_access_to_a_motor_vehicle = row[7]
            self.no_one_has_completed_year_12_or_higher = row[8]
            self.moved_to_the_region_in_the_last_1_year = row[9]
            self.moved_to_the_region_in_the_last_5_years = row[10]
            self.top_5_employing_industries = row[11]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'demo.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                all_aged_65_and_over=self.all_aged_65_and_over,
                includes_persons_aged_14_years_and_under=self.includes_persons_aged_14_years_and_under,
                includes_an_indigenous_person=self.includes_an_indigenous_person,
                are_a_single_parent_household=self.are_a_single_parent_household,
                are_in_need_of_assistance_for_self_care_activites=self.are_in_need_of_assistance_for_self_care_activites,
                include_persons_not_proficient_in_english=self.include_persons_not_proficient_in_english,
                do_not_have_access_to_a_motor_vehicle=self.do_not_have_access_to_a_motor_vehicle,
                no_one_has_completed_year_12_or_higher=self.no_one_has_completed_year_12_or_higher,
                moved_to_the_region_in_the_last_1_year=self.moved_to_the_region_in_the_last_1_year,
                moved_to_the_region_in_the_last_5_years=self.moved_to_the_region_in_the_last_5_years,
                top_5_employing_industries=self.top_5_employing_industries
            ),
            status = 200,
                     mimetype = 'text/html'
        )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''


class SA1_ECON(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Economic Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Economic Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_ECON, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_ARE_LOW_INCOME_1_TO_499_WK",
                   "aeip_ARE_MEDIUM_INCOME_500_TO_1499_WK",
                   "aeip_ARE_HIGH_INCOME_1500_PLUS_WK",
                   "aeip_ARE_IN_PUBLIC_HOUSING",
                   "aeip_ARE_ALL_UNEMPLOYED",                            
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 Economic Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.are_low_income_1_to_499_wk = row[1]
            self.are_medium_income_500_to_1499_wk = row[2]
            self.are_high_income_1500_plus_wk = row[3]
            self.are_in_public_housing = row[4]
            self.are_all_unemployed = row[5]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'econ.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                are_low_income_1_to_499_wk=self.are_low_income_1_to_499_wk,
                are_medium_income_500_to_1499_wk=self.are_medium_income_500_to_1499_wk,
                are_high_income_1500_plus_wk=self.are_high_income_1500_plus_wk,
                are_in_public_housing=self.are_in_public_housing,
                are_all_unemployed=self.are_all_unemployed
            ),
            status = 200,
                     mimetype = 'text/html'
            )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''


class SA1_INST(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Institution Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Institution Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_INST, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_SCHOOL_PRE_PRIMARY",
                   "aeip_SCHOOL_SECONDARY",
                   "aeip_SCHOOL_TERTIARY",
                   "aeip_SCHOOL_OTHER",
                   "aeip_HOSPITAL_PUBLIC",
                   "aeip_HOSPITAL_PRIVATE",
                   "aeip_NURSING_HOME",
                   "aeip_RETIREMENT_HOME",
                   "aeip_POLICE_STATION",
                   "aeip_FIRE_STATION",
                   "aeip_AMBULANCE_STATION",
                   "aeip_SES_FACILITY",
                   "aeip_EMERGENCY_MANAGEMENT_FACILITIES",
                   "aeip_FEDERAL_COURT",
                   "aeip_MEDICARE_OFFICE",
                   "aeip_CENTRELINK_OFFICE",
                   "aeip_DIPLOMATIC_FACILITY",
                   "aeip_CONSULATE_FACILITY",
                   "aeip_MAJOR_DEFENCE_FACILITY",
                   "aeip_CORRECTIONAL_FACILITY",
                   "aeip_IMMIGRATION_DETENTION_FACILITY",
                   "aeip_LOCAL_GOVERNMENT_OFFICE",  
    
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 Institution Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.school_pre_primary = row[1]
            self.school_secondary = row[2]
            self.school_tertiary = row[3]
            self.school_other = row[4]
            self.hospital_public = row[5]
            self.hospital_private = row[6]
            self.nursing_home = row[7]
            self.retirement_home = row[8]
            self.police_station = row[9]
            self.fire_station = row[10]
            self.ambulance_station = row[11]
            self.ses_facility = row[12]
            self.emergency_management_facility = row[13]
            self.federal_court = row[14]
            self.medicare_office = row[15]
            self.centrelink_office = row[16]
            self.diplomatic_facility = row[17]
            self.consulate_facility = row[18]
            self.major_defence_facility = row[19]
            self.correctional_facility = row[20]
            self.immigration_detention_facility = row[21]
            self.local_government_office = row[22]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'inst.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                school_pre_primary=self.school_pre_primary,
                school_secondary=self.school_secondary,
                school_tertiary=self.school_tertiary,
                school_other=self.school_other,
                hospital_public=self.hospital_public,
                hospital_private=self.hospital_private,
                nursing_home=self.nursing_home,
                retirement_home=self.retirement_home,
                police_station=self.police_station,
                fire_station=self.fire_station,
                ambulance_station=self.ambulance_station,
                ses_facility=self.ses_facility,
                emergency_management_facility=self.emergency_management_facility,
                federal_court=self.federal_court,
                medicare_office=self.medicare_office,
                centrelink_office=self.centrelink_office,
                diplomatic_facility=self.diplomatic_facility,
                consulate_facility=self.consulate_facility,
                major_defence_facility=self.major_defence_facility,
                correctional_facility=self.correctional_facility,
                immigration_detention_facility=self.immigration_detention_facility,
                local_government_office=self.local_government_office
            ),
            status = 200,
                     mimetype = 'text/html'
            )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''


class SA1_TRANSPORT(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Infrastructure-Transport Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Infrastructure-Transport Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_TRANSPORT, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_AIRPORT_MAJOR_AREAS",
                   "aeip_AIRPORT_MAJOR_TERMINALS",
                   "aeip_AIRPORT_LANDING_GROUNDS",
                   "aeip_ROADS_MAJOR_KMS",
                   "aeip_ROADS_ARTERIAL_AND_SUB_ARTERIAL_KMS",
                   "aeip_RAILWAY_TRACKS_KMS",
                   "aeip_RAILWAY_STATIONS",
                   "aeip_MARITIME_MAJOR_PORT",
                   "aeip_MARITIME_FERRY_TERMINAL",
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 Infrastructure-Transport Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.airport_major_areas = row[1]
            self.airport_major_terminals = row[2]
            self.airport_landing_grounds = row[3]
            self.roads_major_kms = row[4]
            self.roads_arterial_and_sub_arterial_kms = row[5]
            self.railway_track_kms = row[6]
            self.railway_stations = row[7]
            self.maritime_major_port = row[8]
            self.maritime_ferry_terminal = row[9]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'transport.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                airport_major_areas=self.airport_major_areas,
                airport_major_terminals=self.airport_major_terminals,
                airport_landing_grounds=self.airport_landing_grounds,
                roads_major_kms=self.roads_major_kms,
                roads_arterial_and_sub_arterial_kms=self.roads_arterial_and_sub_arterial_kms,
                railway_track_kms=self.railway_track_kms,
                railway_stations=self.railway_stations,
                maritime_major_port=self.maritime_major_port,
                maritime_ferry_terminal=self.maritime_ferry_terminal,
            ),
            status=200,
            mimetype='text/html'
        )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''



class SA1_TRANSPORT(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Infrastructure-Transport Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Infrastructure-Transport Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_TRANSPORT, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_AIRPORT_MAJOR_AREAS",
                   "aeip_AIRPORT_MAJOR_TERMINALS",
                   "aeip_AIRPORT_LANDING_GROUNDS",
                   "aeip_ROADS_MAJOR_KMS",
                   "aeip_ROADS_ARTERIAL_AND_SUB_ARTERIAL_KMS",
                   "aeip_RAILWAY_TRACKS_KMS",
                   "aeip_RAILWAY_STATIONS",
                   "aeip_MARITIME_MAJOR_PORT",
                   "aeip_MARITIME_FERRY_TERMINAL",
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 Infrastructure-Transport Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.airport_major_areas = row[1]
            self.airport_major_terminals = row[2]
            self.airport_landing_grounds = row[3]
            self.roads_major_kms = row[4]
            self.roads_arterial_and_sub_arterial_kms = row[5]
            self.railway_track_kms = row[6]
            self.railway_stations = row[7]
            self.maritime_major_port = row[8]
            self.maritime_ferry_terminal = row[9]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'transport.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                airport_major_areas=self.airport_major_areas,
                airport_major_terminals=self.airport_major_terminals,
                airport_landing_grounds=self.airport_landing_grounds,
                roads_major_kms=self.roads_major_kms,
                roads_arterial_and_sub_arterial_kms=self.roads_arterial_and_sub_arterial_kms,
                railway_track_kms=self.railway_track_kms,
                railway_stations=self.railway_stations,
                maritime_major_port=self.maritime_major_port,
                maritime_ferry_terminal=self.maritime_ferry_terminal,
            ),
            status=200,
            mimetype='text/html'
        )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''



class SA1_UTILITY(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Infrastructure-Utility Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Infrastructure-Utility Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_UTILITY, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_POWER_STATION_MAJOR_FOSSIL_FUEL",
                   "aeip_POWER_STATION_MAJOR_RENEWABLE",
                   "aeip_TRANSMISSION_SUBSTATION",
                   "aeip_TRANSMISSION_ELECTRICITY_LINES_KMS",
                   "aeip_LIQUID_FUEL_REFINERIES",
                   "aeip_LIQUID_FUEL_TERMINALS",
                   "aeip_LIQUID_FUEL_DEPOTS",
                   "aeip_LIQUID_FUEL_PETROL_STATIONS",
                   "aeip_GAS_PIPELINES_KMS",
                   "aeip_OIL_PIPELINES_KMS",
                   "aeip_OFFSHORE_EXTRACTION_PLATFORM",
                   "aeip_WASTE_MANAGEMENT_SITE",
                   "aeip_WASTE_WATER_TREATMENT_PLANT",
                   "aeip_MAJOR_DAM_WALLS",
                   "aeip_TELEPHONE_EXCHANGE",
                   "aeip_BROADCASTING_STUDIO_RADIO_TV",
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 Infrastructure-Utility Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.power_station_major_fossil_fuel = row[1]
            self.power_station_major_renewable = row[2]
            self.transmission_substation= row[3]
            self.transmission_electricity_lines_kms = row[4]
            self.liquid_fuel_refineries = row[5]
            self.liquid_fuel_terminals = row[6]
            self.liquid_fuel_depots = row[7]
            self.liquid_fuel_petrol_stations = row[8]
            self.gas_pipelines_kms = row[9]
            self.oil_pipelines_kms = row[10]
            self.offshore_extraction_platform = row[11]
            self.waste_management_site = row[12]
            self.waste_water_treatment_plant = row[13]
            self.major_dam_walls = row[14]
            self.telephone_exchange = row[15]
            self.broadcasting_studio_radio_tv = row[16]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'utility.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                power_station_major_fossil_fuel=self.power_station_major_fossil_fuel,
                power_station_major_renewable=self.power_station_major_renewable,
                transmission_substation=self.transmission_substation,
                transmission_electricity_lines_kms=self.transmission_electricity_lines_kms,
                liquid_fuel_refineries=self.liquid_fuel_refineries,
                liquid_fuel_terminals=self.liquid_fuel_terminals,
                liquid_fuel_depots=self.liquid_fuel_depots,
                liquid_fuel_petrol_stations=self.liquid_fuel_petrol_stations,
                gas_pipelines_kms=self.gas_pipelines_kms,
                oil_pipelines_kms=self.oil_pipelines_kms,
                offshore_extraction_platform=self.offshore_extraction_platform,
                waste_management_site=self.waste_management_site,
                waste_water_treatment_plant=self.waste_water_treatment_plant,
                major_dam_walls=self.major_dam_walls,
                telephone_exchange=self.telephone_exchange,
                broadcasting_studio_radio_tv=self.broadcasting_studio_radio_tv,
            ),
            status=200,
            mimetype='text/html'
        )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''



class SA1_BUSINESS(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Business Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Business Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_BUSINESS, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_ACCOMMODATION_AND_FOOD_SERVICES",
                   "aeip_ADMINISTRATIVE_AND_SUPPORT_SERVICES",
                   "aeip_AGRICULTURE_FORESTRY_FISHING",
                   "aeip_ARTS_AND_RECREATION_SERVICES",
                   "aeip_CONSTRUCTION",
                   "aeip_EDUCATION_AND_TRAINING",
                   "aeip_ELECT_GAS_WATER_WASTE_SERVICES",
                   "aeip_FINANCIAL_AND_INSURANCE_SERVICES",
                   "aeip_HEALTH_CARE_AND_SOCIAL_ASSISTANCE",
                   "aeip_INFORMATION_MEDIA_AND_TELECOMMUNICATIONS",
                   "aeip_MANUFACTURING",
                   "aeip_MINING",
                   "aeip_OTHER_SERVICES",
                   "aeip_PROFESSIONAL_SCIENTIFIC_AND_TECHNICAL_SERVICES",
                   "aeip_PUBLIC_ADMINISTRATION_AND_SAFETY",
                   "aeip_RENTAL_HIRING_AND_REAL_ESTATE_SERVICES",
                   "aeip_RETAIL_TRADE",
                   "aeip_TRANSPORT_POSTAL_AND_WAREHOUSING",
                   "aeip_WHOLESALE_TRADE",
                   "aeip_UNCLASSIFIED_BUSINESSES",
                   "aeip_TOTAL_NUMBER_OF_BUSINESSES",
                   "aeip_NUMBER_OF_REGISTERED_CHARITY_ORGANISATIONS",
                   "aeip_AGRICULTURE_AND_FISHING_SUPPORT_SERVICES",
                   "aeip_AQUACULTURE",
                   "aeip_DAIRY_CATTLE_FARMING",
                   "aeip_DEER_FARMING",
                   "aeip_FISHING",
                   "aeip_FORESTRY_AND_LOGGING",
                   "aeip_FORESTRY_SUPPORT_SERVICES",
                   "aeip_FRUIT_AND_TREE_NUT_GROWING",
                   "aeip_HUNTING_AND_TRAPPING",
                   "aeip_MUSHROOM_AND_VEGETABLE_GROWING",
                   "aeip_NURSERY_AND_FLORICULTURE_PRODUCTION",
                   "aeip_OTHER_CROP_GROWING",
                   "aeip_OTHER_LIVESTOCK_FARMING",
                   "aeip_POULTRY_FARMING",
                   "aeip_SHEEP_BEEF_CATTLE_AND_GRAIN_FARMING",
                   "aeip_TOTAL_NUMBER_OF_PRIMARY_PRODUCERS",                   
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 Business Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.accommodation_and_food_services = row[1]
            self.administrative_and_support_services = row[2]
            self.agriculture_forestry_fishing= row[3]
            self.arts_and_recreation_services = row[4]
            self.construction = row[5]
            self.education_and_training = row[6]
            self.elect_gas_water_waste_services = row[7]
            self.financial_and_insurance_services = row[8]
            self.health_care_and_social_assistance = row[9]
            self.information_media_and_telecommunications = row[10]
            self.manufacturing = row[11]
            self.mining = row[12]
            self.other_services = row[13]
            self.professional_scientific_and_technical_services = row[14]
            self.public_administration_and_safety = row[15]
            self.rental_hiring_and_real_estate_services = row[16]
            self.retail_trade = row[17]
            self.transport_postal_and_warehousing = row[18]
            self.wholesale_trade = row[19]
            self.unclassified_businesses = row[20]
            self.total_number_of_businesses = row[21]
            self.number_of_registered_charity_organisations = row[22]
            self.agriculture_and_fishing_support_services = row[23]
            self.aquaculture = row[24]
            self.dairy_cattle_farming = row[25]
            self.deer_farming = row[26]
            self.fishing = row[27]
            self.forestry_and_logging = row[28]
            self.forestry_support_services = row[29]
            self.fruit_and_tree_nut_growing = row[30]
            self.hunting_and_trapping = row[31]
            self.mushroom_and_vegetable_growing = row[32]
            self.nursery_and_floriculture_production = row[33]
            self.other_crop_growing = row[34]
            self.other_livestock_farming = row[35]
            self.poultry_farming = row[36]
            self.sheep_beef_cattle_and_grain_farming = row[37]
            self.total_number_of_primary_producers = row[38]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'business.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                accommodation_and_food_services=self.accommodation_and_food_services,
                administrative_and_support_services=self.administrative_and_support_services,
                agriculture_forestry_fishing=self.agriculture_forestry_fishing,
                arts_and_recreation_services=self.arts_and_recreation_services,
                construction=self.construction,
                education_and_training=self.education_and_training,
                elect_gas_water_waste_services=self.elect_gas_water_waste_services,
                financial_and_insurance_services=self.financial_and_insurance_services,
                health_care_and_social_assistance=self.health_care_and_social_assistance,
                information_media_and_telecommunications=self.information_media_and_telecommunications,
                manufacturing=self.manufacturing,
                mining=self.mining,
                other_services=self.other_services,
                professional_scientific_and_technical_services=self.professional_scientific_and_technical_services,
                public_administration_and_safety=self.public_administration_and_safety,
                rental_hiring_and_real_estate_services=self.rental_hiring_and_real_estate_services,
                retail_trade=self.retail_trade,
                transport_postal_and_warehousing=self.transport_postal_and_warehousing,
                wholesale_trade=self.wholesale_trade,
                unclassified_businesses=self.unclassified_businesses,
                total_number_of_businesses=self.total_number_of_businesses,
                number_of_registered_charity_organisations=self.number_of_registered_charity_organisations,
                agriculture_and_fishing_support_services=self.agriculture_and_fishing_support_services,
                aquaculture=self.aquaculture,
                dairy_cattle_farming=self.dairy_cattle_farming,
                deer_farming=self.deer_farming,
                fishing=self.fishing,
                forestry_and_logging=self.forestry_and_logging,
                forestry_support_services=self.forestry_support_services,
                fruit_and_tree_nut_growing=self.fruit_and_tree_nut_growing,
                hunting_and_trapping=self.hunting_and_trapping,
                mushroom_and_vegetable_growing=self.mushroom_and_vegetable_growing,
                nursery_and_floriculture_production=self.nursery_and_floriculture_production,
                other_crop_growing=self.other_crop_growing,
                other_livestock_farming=self.other_livestock_farming,
                poultry_farming=self.poultry_farming,
                sheep_beef_cattle_and_grain_farming=self.sheep_beef_cattle_and_grain_farming,
                total_number_of_primary_producers=self.total_number_of_primary_producers
            ),
            status=200,
            mimetype='text/html'
        )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''



class SA1_AGRI(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Agriculture Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Agriculture Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_AGRI, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
           SELECT
               "SA1_MAIN16",
               "aeip_ESTIMATED_VACP_VALUE",
               "aeip_ESTIMATED_AGRICULTURAL_AREA_HA",
               "aeip_COMMODITY_LIST",               
               ST_AsGeoJSON(geom) As geom
           FROM "{}"
           WHERE "id" = '{}'
       '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 AEIP Agriculture Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.estimated_vacp_value = row[1]
            self.estimated_agricultural_area_ha = row[2]
            self.commodity_list = row[3]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'agri.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                estimated_vacp_value=self.estimated_vacp_value,
                estimated_agricultural_area_ha=self.estimated_agricultural_area_ha,
                commodity_list=self.commodity_list
            ),
            status = 200,
                     mimetype = 'text/html'
        )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''



class SA1_ENVI(Renderer):
    """
    This class represents a placename and methods in this class allow a placename to be loaded from the GA placenames
    database and to be exported in a number of formats including RDF, according to the 'PlaceNames Ontology'

    [[and an expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.]]??
    """

    def __init__(self, request, uri):
        format_list = ['text/html', 'text/turtle', 'application/ld+json', 'application/rdf+xml']
        profiles = {
            'SA1_AEIP': Profile(
                'http://linked.data.gov.au/def/SA1/',
                'SA1 Environment Exposure View',
                'This view is produced from the AEIP SA1 dataset'
                ' in accordance with the Environment Profile',
                format_list,
                'text/html'
            )
        }

        super(SA1_ENVI, self).__init__(request, uri, profiles, 'SA1_AEIP')

        self.id = uri.split('/')[-1]

        q = '''
               SELECT
                   "SA1_MAIN16",
                   "aeip_WH_FEATURES",
                   "aeip_WH_TOTAL_AREA",
                   "aeip_WH_BUFFER_FEATURES",
                   "aeip_WH_TOTAL_BUFFER_AREA",
                   "aeip_NH_HISTORIC_FEATURES",
                   "aeip_NH_TOTAL_HISTORIC_AREA",
                   "aeip_NH_INDIGENOUS_FEATURES",
                   "aeip_NH_TOTAL_INDIGENOUS_AREA",
                   "aeip_NH_NATURAL_FEATURES",
                   "aeip_NH_TOTAL_NATURAL_AREA",
                   "aeip_CH_HISTORIC_FEATURES",
                   "aeip_CH_TOTAL_HISTORIC_AREA",
                   "aeip_CH_INDIGENOUS_FEATURES",
                   "aeip_CH_TOTAL_INDIGENOUS_AREA",
                   "aeip_CH_NATURAL_FEATURES",
                   "aeip_CH_TOTAL_NATURAL_AREA",
                   "aeip_CAPAD_IA_FEATURES",
                   "aeip_CAPAD_IA_TOTAL_AREA",
                   "aeip_CAPAD_IB_FEATURES",
                   "aeip_CAPAD_IB_TOTAL_AREA",
                   "aeip_CAPAD_II_FEATURES",
                   "aeip_CAPAD_II_TOTAL_AREA",
                   "aeip_CAPAD_III_FEATURES",
                   "aeip_CAPAD_III_TOTAL_AREA",
                   "aeip_CAPAD_IV_FEATURES",
                   "aeip_CAPAD_IV_TOTAL_AREA",
                   "aeip_CAPAD_V_FEATURES",
                   "aeip_CAPAD_V_TOTAL_AREA",
                   "aeip_CAPAD_VI_FEATURES",
                   "aeip_CAPAD_VI_TOTAL_AREA",
                   "aeip_RAMSAR_FEATURES",
                   "aeip_RAMSAR_TOTAL_AREA",
                   "aeip_IBRA_FEATURES",
                   "aeip_IBRA_TOTAL_AREA",
                   "aeip_NRM_FEATURES",
                   "aeip_NRM_TOTAL_AREA",                   
                   ST_AsGeoJSON(geom) As geom
               FROM "{}"
               WHERE "id" = '{}'
           '''.format(TABLE_NAME, self.id)

        self.hasName = {
            'uri': 'http://linked.data.gov.au/def/SA1/',
            'label': 'SA1 Environment Exposure',
            'comment': 'The Entity has a name (label) which is a text string.',
            'value': None
        }

        self.featureCords = []
        for row in conf.db_select(q):
            self.hasName['value'] = str(row[0])
            self.wh_features = row[1]
            self.wh_total_area = row[2]
            self.wh_buffer_features= row[3]
            self.wh_total_buffer_area = row[4]
            self.nh_historic_features = row[5]
            self.nh_total_historic_area = row[6]
            self.nh_indigenous_features = row[7]
            self.nh_total_indigenous_area = row[8]
            self.nh_natural_features = row[9]
            self.nh_total_natural_area = row[10]
            self.ch_historic_features = row[11]
            self.ch_total_historic_area = row[12]
            self.ch_indigenous_features = row[13]
            self.ch_total_indigenous_area = row[14]
            self.ch_natural_features = row[15]
            self.ch_total_natural_area = row[16]
            self.capad_ia_features = row[17]
            self.capad_ia_total_area = row[18]
            self.capad_ib_features = row[19]
            self.capad_ib_total_area = row[20]
            self.capad_ii_features = row[21]
            self.capad_ii_total_area = row[22]
            self.capad_iii_features = row[23]
            self.capad_iii_total_area = row[24]
            self.capad_iv_features = row[25]
            self.capad_iv_total_area = row[26]
            self.capad_v_features = row[27]
            self.capad_v_total_area = row[28]
            self.capad_vi_features = row[29]
            self.capad_vi_total_area = row[30]
            self.ramsar_features = row[31]
            self.ramsar_total_area = row[32]
            self.ibra_features = row[33]
            self.ibra_total_area = row[34]
            self.nrm_features = row[35]
            self.nrm_total_area = row[36]

            # get geometry from database
            self.geom = ast.literal_eval(row[-1])
            self.featureCords = self.geom['coordinates']
            self.geometry_type = self.geom['type']

    def export_html(self, model_view='SA1_AEIP'):
        html_page = 'envi.html'
        return Response(  # Response is a Flask class imported at the top of this script
            render_template(  # render_template is also a Flask module
                html_page,  # uses the html template to send all this data to it.
                id=self.id,
                hasName=self.hasName,
                coordinate_list=self.featureCords,
                geometry_type=self.geometry_type,
                wh_features=self.wh_features,
                wh_total_area=self.wh_total_area,
                wh_buffer_features=self.wh_buffer_features,
                wh_total_buffer_area=self.wh_total_buffer_area,
                nh_historic_features=self.nh_historic_features,
                nh_total_historic_area=self.nh_total_historic_area,
                nh_indigenous_features=self.nh_indigenous_features,
                nh_total_indigenous_area=self.nh_total_indigenous_area,
                nh_natural_features=self.nh_natural_features,
                nh_total_natural_area=self.nh_total_natural_area,
                ch_historic_features=self.ch_historic_features,
                ch_total_historic_area=self.ch_total_historic_area,
                ch_indigenous_features=self.ch_indigenous_features,
                ch_total_indigenous_area=self.ch_total_indigenous_area,
                ch_natural_features=self.ch_natural_features,
                ch_total_natural_area=self.ch_total_natural_area,
                capad_ia_features=self.capad_ia_features,
                capad_ia_total_area=self.capad_ia_total_area,
                capad_ib_features=self.capad_ib_features,
                capad_ib_total_area=self.capad_ib_total_area,
                capad_ii_features=self.capad_ii_features,
                capad_ii_total_area=self.capad_ii_total_area,
                capad_iii_features=self.capad_iii_features,
                capad_iii_total_area=self.capad_iii_total_area,
                capad_iv_features=self.capad_iv_features,
                capad_iv_total_area=self.capad_iv_total_area,
                capad_v_features=self.capad_v_features,
                capad_v_total_area=self.capad_v_total_area,
                capad_vi_features=self.capad_vi_features,
                capad_vi_total_area=self.capad_vi_total_area,
                ramsar_features=self.ramsar_features,
                ramsar_total_area=self.ramsar_total_area,
                ibra_features=self.ibra_features,
                ibra_total_area=self.ibra_total_area,
                nrm_features=self.nrm_features,
                nrm_total_area=self.nrm_total_area
            ),
            status=200,
            mimetype='text/html'
        )

    def render(self):
        if self.profile == 'alt':
            return self._render_alt_profile()  # this function is in Renderer
        elif self.mediatype in ['text/turtle', 'application/ld+json', 'application/rdf+xml']:
            return self.export_rdf(self.profile)
        else:  # default is HTML response: self.format == 'text/html':
            return self.export_html(self.profile)

    def _generate_dggs(self):
        if self.id is not None and self.thisFeature is not None:
            dggs_uri = []
            for item in self.thisFeature:
                dggs_uri.append(item['uri'])
            return '{}'.format(dggs_uri)
        else:
            return ''




if __name__ == '__main__':
    pass




