from xml.dom.minidom import Document
import string
import os
import glob

# create output project file
f = open('../../Compare.qgs','w')
doc = Document()

# create <qgis> element
qgis = doc.createElement("qgis")
qgis.setAttribute("version", "3.4.1-Madeira")
qgis.setAttribute("projectname", "Compare")
doc.appendChild(qgis)

#nesting
homePath = doc.createElement('homePath')
homePath.setAttribute('path','')
qgis.appendChild(homePath)

title = doc.createElement("title")
qgis.appendChild(title)

tags=['autotransaction', 'evaluateDefaultValues','trust']
for t in tags:
    t=doc.createElement(t)
    t.setAttribute('active','0')
    qgis.appendChild(t)

projectCrs = doc.createElement("projectCrs")
qgis.appendChild(projectCrs)

spatialrefsys = doc.createElement("spatialrefsys")
projectCrs.appendChild(spatialrefsys)

#TODO: remove hardcoded parameters, upload dynamically
spatialRefSys_Tag = ['proj4','srsid','srid','authid','description','projectionacronym','ellipsoidacronym','geographicflag']
spatialRefSys_Text = ['+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs','2106','25833','EPSG:25833','ETRS89 / UTM zone 33N','utm','GRS80','false']

for p in range(len(spatialRefSys_Tag)):
    temp = doc.createTextNode(spatialRefSys_Text[p])
    spatialRefSys_Tag[p] = doc.createElement(spatialRefSys_Tag[p])
    spatialRefSys_Tag[p].appendChild(temp)
    spatialrefsys.appendChild(spatialRefSys_Tag[p])

#layer-tree-group - problem with dashes
'''
layer-tree-group = doc.createElement('layer-tree-group')
qgis.appendChild(layer-tree-group)

customproperties = doc.createElement('customproperties')
layer-tree-group.appendChild(customproperties)
'''

unit = doc.createTextNode("degrees")
xmin1 = doc.createTextNode(str("-180"))
ymin1 = doc.createTextNode(str("-90"))
xmax1 = doc.createTextNode(str("180"))
ymax1 = doc.createTextNode(str("90"))
proj4id = doc.createTextNode(str("+proj=longlat +datum=WGS84 +no_defs"))
srid1 = doc.createTextNode(str("4326"))
srid2 = doc.createTextNode(str("3452"))
epsg1 = doc.createTextNode(str("4326"))
epsg2 = doc.createTextNode(str("4326"))
description1 = doc.createTextNode(str("WGS 84"))
description2 = doc.createTextNode(str("WGS 84"))
ellipsoidacronym1 = doc.createTextNode(str("WGS84"))
ellipsoidacronym2 = doc.createTextNode(str("WGS84"))
geographicflag1 = doc.createTextNode("true")
geographicflag2 = doc.createTextNode("true")
pa=doc.createTextNode("longlat")
authid2 = doc.createTextNode("EPSG:"+str("4326"))
authid3 = doc.createTextNode("EPSG:"+str("4326"))
count2=0

# mapcanvas
def map_canvas():
    # Create the <mapcanvas> element
    mapcanvas = doc.createElement("mapcanvas")
    qgis.appendChild(mapcanvas)

    # Create the <units> element
    units = doc.createElement("units") #text maybe?
    units.appendChild(unit)
    mapcanvas.appendChild(units)

    # Create the <extent> element
    extent = doc.createElement("extent")
    mapcanvas.appendChild(extent)

    # Create the <xmin> element
    xmin = doc.createElement("xmin")
    xmin.appendChild(xmin1)
    extent.appendChild(xmin)

    # Create the <ymin> element
    ymin = doc.createElement("ymin")
    ymin.appendChild(ymin1)
    extent.appendChild(ymin)

    # Create the <xmax> element
    xmax = doc.createElement("xmax")
    xmax.appendChild(xmax1)
    extent.appendChild(xmax)

    # Create the <ymax> element
    ymax = doc.createElement("ymax")
    ymax.appendChild(ymax1)
    extent.appendChild(ymax)

    # Create the <projections> element
    projections = doc.createElement("projections")
    mapcanvas.appendChild(projections)

    # Create the <destinationsrs> element
    destinationsrs = doc.createElement("destinationsrs")
    mapcanvas.appendChild(destinationsrs)

    # Create the <spatialrefsys> element
    spatialrefsys = doc.createElement("spatialrefsys")
    destinationsrs.appendChild(spatialrefsys)

    # Create the <proj4> element
    proj4 = doc.createElement("proj4")
    proj4.appendChild(proj4id)
    spatialrefsys.appendChild(proj4)

    # Create the <srsid> element
    srsid = doc.createElement("srsid")
    srsid.appendChild(srid2)
    spatialrefsys.appendChild(srsid)

    # Create the <srid> element
    srid = doc.createElement("srid")
    srid.appendChild(srid1)
    spatialrefsys.appendChild(srid)

    # Create the <authid> element
    authid = doc.createElement("authid")
    authid.appendChild(authid2)
    spatialrefsys.appendChild(authid)

    # Create the <description> element
    description = doc.createElement("description")
    description.appendChild(description1)
    spatialrefsys.appendChild(description)

    # Create the <projectionacronym> element
    projectionacronym = doc.createElement("projectionacronym")
    spatialrefsys.appendChild(projectionacronym)
    projectionacronym.appendChild(pa)

    # Create the <ellipsoidacronym element
    ellipsoidacronym = doc.createElement("ellipsoidacronym")
    ellipsoidacronym.appendChild(ellipsoidacronym1)
    spatialrefsys.appendChild(ellipsoidacronym)

    # Create the <geographicflag> element
    geographicflag = doc.createElement("geographicflag")
    geographicflag.appendChild(geographicflag1)
    spatialrefsys.appendChild(geographicflag)

# Legend
def legend_func():
    global count2
    # Create the <legend> element
    legend = doc.createElement("legend")
    qgis.appendChild(legend)


    for lyr in os.listdir(r'..\..\data\output'):
         if lyr.endswith('.tif'):
            count2=count2+1
            #print(lyr)
            #print('\n')
            
            # Create the <legendlayer> element
            legendlayer = doc.createElement("legendlayer")
            legendlayer.setAttribute("open", "true")
            legendlayer.setAttribute("checked", "Qt::Checked")
            legendlayer.setAttribute("name",lyr)

            legend.appendChild(legendlayer)

            # Create the <filegroup> element
            filegroup = doc.createElement("filegroup")
            filegroup.setAttribute("open", "true")
            filegroup.setAttribute("hidden", "false")
            legendlayer.appendChild(filegroup)

            # Create the <legendlayerfile> element
            legendlayerfile = doc.createElement("legendlayerfile")
            legendlayerfile.setAttribute("isInOverview", "0")
            legendlayerfile.setAttribute("layerid", lyr+str(20110427170816078))
            legendlayerfile.setAttribute("visible", "1")
            filegroup.appendChild(legendlayerfile)

# Project Layers
def project_layers():  
    # Create the <projectlayers> element
    projectlayers = doc.createElement("projectlayers")
    count1=str(count2)
    projectlayers.setAttribute("layercount", count1)
    qgis.appendChild(projectlayers)

    #TODO: change directory
    for lyr in os.listdir(r'..\..\data\output'):
        if lyr.endswith('.tif'):
            print(lyr)
            print("\n")
            ds = doc.createTextNode(str(r'..\..\data\output'+"\\"+lyr))

            name1 = doc.createTextNode(lyr+str(20110427170816078))
            name = doc.createTextNode(lyr)

            # create <maplayer> element
            maplayer = doc.createElement("maplayer")
            projectlayers.appendChild(maplayer)


            # Create the <id> element
            id = doc.createElement("id")
            id.appendChild(name1)
            maplayer.appendChild(id)

            # Create the <datasource> element
            datasource = doc.createElement("datasource")
            datasource.appendChild(ds)
            maplayer.appendChild(datasource)

            # Create the <layername> element
            layername = doc.createElement("layername")
            layername.appendChild(name)
            maplayer.appendChild(layername)


            # Create the <srs> element
            srs = doc.createElement("srs")
            maplayer.appendChild(srs)

            # Create the <spatialrefsys> element
            spatialrefsys = doc.createElement("spatialrefsys")
            srs.appendChild(spatialrefsys)

            # Create the <proj4> element
            proj4 = doc.createElement("proj4")
            spatialrefsys.appendChild(proj4)

            # Create the <srsid> element
            srsid = doc.createElement("srsid")
            spatialrefsys.appendChild(srsid)

            # Create the <srid> element
            srid = doc.createElement("srid")
            srid.appendChild(srid2)
            spatialrefsys.appendChild(srid)


            # Create the <authid> element
            authid = doc.createElement("authid")
            authid.appendChild(authid3)
            spatialrefsys.appendChild(authid)


            # Create the <description> element
            description = doc.createElement("description")
            description.appendChild(description2)
            spatialrefsys.appendChild(description)


            # Create the <projectionacronym> element
            projectionacronym = doc.createElement("projectionacronym")
            spatialrefsys.appendChild(projectionacronym)

            # Create the <ellipsoidacronym element
            ellipsoidacronym = doc.createElement("ellipsoidacronym")
            ellipsoidacronym.appendChild(ellipsoidacronym2)
            spatialrefsys.appendChild(ellipsoidacronym)


            # Create the <geographicflag> element
            geographicflag = doc.createElement("geographicflag")
            geographicflag.appendChild(geographicflag2)
            spatialrefsys.appendChild(geographicflag)

            # Create the <transparencyLevelInt> element
            transparencyLevelInt = doc.createElement("transparencyLevelInt")
            transparency2 = doc.createTextNode("255")
            transparencyLevelInt.appendChild(transparency2)
            maplayer.appendChild(transparencyLevelInt)

            # Create the <customproperties> element
            customproperties = doc.createElement("customproperties")
            maplayer.appendChild(customproperties)

            # Create the <provider> element
            provider = doc.createElement("provider")
            provider.setAttribute("encoding", "System")
            ogr = doc.createTextNode("ogr")
            provider.appendChild(ogr)
            maplayer.appendChild(provider)

            # Create the <singlesymbol> element
            singlesymbol = doc.createElement("singlesymbol")
            maplayer.appendChild(singlesymbol)

            # Create the <symbol> element
            symbol = doc.createElement("symbol")
            singlesymbol.appendChild(symbol)

            # Create the <lowervalue> element
            lowervalue = doc.createElement("lowervalue")
            symbol.appendChild(lowervalue)

            # Create the <uppervalue> element
            uppervalue = doc.createElement("uppervalue")
            symbol.appendChild(uppervalue)

            # Create the <label> element
            label = doc.createElement("label")
            symbol.appendChild(label)

            # Create the <rotationclassificationfieldname> element
            rotationclassificationfieldname = doc.createElement("rotationclassificationfieldname")
            symbol.appendChild(rotationclassificationfieldname)

            # Create the <scaleclassificationfieldname> element
            scaleclassificationfieldname = doc.createElement("scaleclassificationfieldname")
            symbol.appendChild(scaleclassificationfieldname)

            # Create the <symbolfieldname> element
            symbolfieldname = doc.createElement("symbolfieldname")
            symbol.appendChild(symbolfieldname)

             # Create the <outlinecolor> element
            outlinecolor = doc.createElement("outlinecolor")
            outlinecolor.setAttribute("red", "88")
            outlinecolor.setAttribute("blue", "99")
            outlinecolor.setAttribute("green", "37")
            symbol.appendChild(outlinecolor)

             # Create the <outlinestyle> element
            outlinestyle = doc.createElement("outlinestyle")
            outline = doc.createTextNode("SolidLine")
            outlinestyle.appendChild(outline)
            symbol.appendChild(outlinestyle)

             # Create the <outlinewidth> element
            outlinewidth = doc.createElement("outlinewidth")
            width = doc.createTextNode("0.26")
            outlinewidth.appendChild(width)
            symbol.appendChild(outlinewidth)

             # Create the <fillcolor> element
            fillcolor = doc.createElement("fillcolor")
            fillcolor.setAttribute("red", "90")
            fillcolor.setAttribute("blue", "210")
            fillcolor.setAttribute("green", "229")
            symbol.appendChild(fillcolor)

             # Create the <fillpattern> element
            fillpattern = doc.createElement("fillpattern")
            fill = doc.createTextNode("SolidPattern")
            fillpattern.appendChild(fill)
            symbol.appendChild(fillpattern)

             # Create the <texturepath> element
            texturepath = doc.createElement("texturepath")
            texturepath.setAttribute("null", "1")
            symbol.appendChild(texturepath)

map_canvas()
project_layers()
legend_func()


#  Write to qgis file
try:
    f.write(doc.toprettyxml(indent=' ', newl="\n"))
finally:
    f.close()

print('Done')