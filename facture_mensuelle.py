# -*- coding: utf-8 -*-

##    This file is part of Gertrude.
##
##    Gertrude is free software; you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation; either version 3 of the License, or
##    (at your option) any later version.
##
##    Gertrude is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with Gertrude; if not, see <http://www.gnu.org/licenses/>.

from constants import *
from functions import *
from facture import *
from cotisation import CotisationException
from ooffice import *

couleurs = { SUPPLEMENT: 'A2',
             MALADE: 'B2',
             PRESENT: 'C2',
             VACANCES: 'D2',
             ABSENT: 'E2'}

class FactureModifications(object):
    def __init__(self, inscrits, periode):
        self.template = 'Facture mensuelle.odt'
        self.inscrits = inscrits
        self.periode = periode
        if len(inscrits) > 1:
            self.default_output = u"Factures %s %d.odt" % (months[periode.month - 1], periode.year)
        else:
            who = inscrits[0]
            self.default_output = u"Facture %s %s %s %d.odt" % (who.prenom, who.nom, months[periode.month - 1], periode.year)

    def execute(self, filename, dom):
        if filename != 'content.xml':
            return None

        errors = {}
        
        #print dom.toprettyxml()
        doc = dom.getElementsByTagName("office:text")[0]
        templates = doc.childNodes[:]
        
        for index, inscrit in enumerate(self.inscrits):
            try:
                facture = Facture(inscrit, self.periode.year, self.periode.month)
            except CotisationException, e:
                errors["%s %s" % (inscrit.prenom, inscrit.nom)] = e.errors
                continue
           
            for template in templates:
                section = template.cloneNode(1)
                if section.nodeName in ("draw:frame", "draw:custom-shape"):
                    doc.insertBefore(section, template)
                else:
                    doc.appendChild(section)
                if section.hasAttribute("text:anchor-page-number"):
                    section.setAttribute("text:anchor-page-number", str(index+1))
            
                # D'abord le tableau des presences du mois
                empty_cells = facture.debut_recap.weekday()
                if empty_cells > 4:
                    empty_cells -= 7
        
                # Création d'un tableau de cells
                for table in section.getElementsByTagName('table:table'):
                    if table.getAttribute('table:name') == 'Presences':
                        rows = table.getElementsByTagName('table:table-row')[1:]
                        cells = []
                        for i in range(len(rows)):
                            cells.append(rows[i].getElementsByTagName('table:table-cell'))
                            for cell in cells[i]:
                                cell.setAttribute('table:style-name', 'Tableau1.E2')
                                text_node = cell.getElementsByTagName('text:p')[0]
                                text_node.firstChild.replaceWholeText(' ')
        
                        date = facture.debut_recap
                        while date.month == facture.debut_recap.month:
                            col = date.weekday()
                            if col < 5:
                                details = ""
                                row = (date.day + empty_cells) / 7
                                cell = cells[row][col]
                                # ecriture de la date dans la cellule
                                text_node = cell.getElementsByTagName('text:p')[0]
                                if date in facture.jours_presence_selon_contrat:
                                    state = PRESENT
                                    details = " (%s)" % GetHeureString(facture.jours_presence_selon_contrat[date])
                                elif date in facture.jours_supplementaires:
                                    state = SUPPLEMENT
                                    details = " (%s)" % GetHeureString(facture.jours_supplementaires[date])
                                elif date in facture.jours_maladie:
                                    state = MALADE
                                elif date in facture.jours_vacances:
                                    state = VACANCES
                                else:
                                    state = ABSENT
                                text_node.firstChild.replaceWholeText('%d%s' % (date.day, details))
                                cell.setAttribute('table:style-name', 'Presences.%s' % couleurs[state])
                            date += datetime.timedelta(1)
        
                        for i in range(row + 1, len(rows)):
                            table.removeChild(rows[i])

                # Les champs de la facture
                fields = GetCrecheFields(creche) + GetInscritFields(inscrit) + GetFactureFields(facture)
                ReplaceTextFields(section, fields)

        for template in templates:
            doc.removeChild(template)
        
        #print doc.toprettyxml() 
        return errors
