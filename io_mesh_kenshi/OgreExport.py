#!BPY

"""
Name: 'OGRE for Kenshi (*.MESH)'
Blender: 2.8+
Group: 'Import/Export'
Tooltip: 'Import/Export Kenshi OGRE mesh files'

Author: someone, Kindrad

Based on the Torchlight Impost/Export script by 'Dusho'

Also thanks to'goatman' for his port of Ogre export script from 2.49b to 2.5x,
and 'CCCenturion' for trying to refactor the code to be nicer (to be included)

last edited by Kindrad Oct-29-2021

"""

__author__ = "someone, Kindrad"
__version__ = "2.9.1 29-Oct-2021"

__bpydoc__ = """\
This script imports/exports Kenshi Ogre models into/from Blender.


Supported:<br>
    * import/export of basic meshes
    * import/export of skeleton
    * import/export of animations
    * import/export of vertex weights (ability to import characters and adjust rigs)
    * import/export of vertex colour (RGB)
    * import/export of vertex alpha (Uses second vertex colour layer called Alpha)
    * import/export of shape keys
    * Calculation of tangents and binormals for export


Known issues:<br>
    * imported materials will lose certain informations not applicable to Blender when exported

History:<br>
    * v0.9.3   (18-Oct-2020) - Added prefix ignore: The exportation of skeleton and animations now ignores bones prefixed by "H_".
    * v0.9.2   (15-Oct-2020) - Added kludge to fix bug with animation export consisting of multiple actions where some are missing keyframe data. Verified it works with Blender 2.9
    * v0.9.1   (13-Sep-2019) - Fixed importing skeletons
    * v0.9.0   (07-May-2019) - Switched to Blender 2.80 API
    * v0.8.14  (14-May-2019) - Fixed blender deleting zero length bones
    * v0.8.13  (19-Mar-2019) - Exporting material files is optional
    * v0.8.12  (14-Mar-2019) - Fixed error exporting animation scale keyframes
    * v0.8.11  (26-Feb-2019) - Fixed tangents and binormals for mirrorred uvs
    * v0.8.10  (32-Jan-2019) - Fixed export when mesh has multiple uv sets
    * v0.8.9   (08-Mar-2018) - Added import option to match weight maps and link with a previously imported skeleton
    * v0.8.8   (26-feb-2018) - Fixed export triangulation and custom normals
    * v0.8.7   (01-Feb-2018) - Scene frame rate adjusted on import, Fixed quatenion normalisation
    * v0.8.6   (31-Jan-2018) - Fixed crash exporting animations in blender 2.79
    * v0.8.5   (02-Jan-2018) - Optimisation: Use hashmap for duplicate vertex detection
    * v0.8.4   (20-Nov-2017) - Fixed animation quaternion interpolation
    * v0.8.3   (06-Nov-2017) - Warning when linked skeleton file not found
    * v0.8.2   (25-Sep-2017) - Fixed bone translations in animations
    * v0.8.1   (28-Jul-2017) - Added alpha component to vertex colour
    * v0.8.0   (30-Jun-2017) - Added animation and shape key support. Rewritten skeleton export
    * v0.7.2   (08-Dec-2016) - fixed divide by 0 error calculating tangents
    * v0.7.1   (07-Sep-2016) - bug fixes
    * v0.7.0   (02-Sep-2016) - Implemented changes needed for Kenshi: Persistant Ogre bone IDs, Export vertex colours. Generates tangents and binormals.
    * v0.6.2   (09-Mar-2013) - bug fixes (working with materials+textures), added 'Apply modifiers' and 'Copy textures'
    * v0.6.1   (27-Sep-2012) - updated to work with Blender 2.63a
    * v0.6     (01-Sep-2012) - added skeleton import + vertex weights import/export
    * v0.5     (06-Mar-2012) - added material import/export
    * v0.4.1   (29-Feb-2012) - flag for applying transformation, default=true
    * v0.4     (28-Feb-2012) - fixing export when no UV data are present
    * v0.3     (22-Feb-2012) - WIP - started cleaning + using OgreXMLConverter
    * v0.2     (19-Feb-2012) - WIP - working export of geometry and faces
    * v0.1     (18-Feb-2012) - initial 2.59 import code (from .xml)
    * v0.0     (12-Feb-2012) - file created
"""

#from Blender import *
from xml.dom import minidom
import bpy
from mathutils import Vector, Matrix, Quaternion
import math
import os
import subprocess
import shutil

SHOW_EXPORT_DUMPS = False
SHOW_EXPORT_TRACE = False
SHOW_EXPORT_TRACE_VX = False

# default blender version of script
blender_version = 259

def hash_combine(x, y):
    return x ^ y + 0x9e3779b9 + (x<<6) + (x>>2)

class VertexInfo(object):
    def __init__(self, px,py,pz, nx,ny,nz, u,v, r,g,b,a, boneWeights, original, tangent, binormal):
        self.px = px
        self.py = py
        self.pz = pz
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.u = u
        self.v = v
        self.r = r
        self.g = g
        self.b = b
        self.a = a
        self.tangent = tangent
        self.binormal = binormal
        self.boneWeights = boneWeights
        self.original = original


    '''does not compare ogre_vidx (and position at the moment) [ no need to compare position ]'''
    def __eq__(self, o):
        if self.nx != o.nx or self.ny != o.ny or self.nz != o.nz: return False
        elif self.px != o.px or self.py != o.py or self.pz != o.pz: return False
        elif self.u != o.u or self.v != o.v: return False
        elif self.r != o.r or self.g != o.g or self.b != o.b: return False
        elif self.tangent and self.tangent[3] != o.tangent[3]: return False;
        return True

    def __hash__(self):
        result = hash(self.px)
        result = hash_combine( result, hash(self.py) )
        result = hash_combine( result, hash(self.pz) )
        result = hash_combine( result, hash(self.nx) )
        result = hash_combine( result, hash(self.ny) )
        result = hash_combine( result, hash(self.nz) )
        result = hash_combine( result, hash(self.u) )
        result = hash_combine( result, hash(self.v) )
        result = hash_combine( result, hash(self.r) )
        result = hash_combine( result, hash(self.g) )
        result = hash_combine( result, hash(self.b) )
        if self.tangent: result = hash_combine( result, hash(self.tangent[3]) )
        return result


########################################

class Bone(object):
    def __init__(self, bone):
        self.name = bone.name
        self.parent = bone.parent.name if bone.parent else None

class Skeleton(object):
    def __init__( self, ob ):
        self.armature = ob.find_armature()
        self.name = self.armature.name
        self.ids = {}
        self.hidden = self.armature.hide_viewport
        data = self.armature.data
        self.armature.hide_viewport = False

        #track bone count
        self.highestBoneID = 0

        # get ogre bone ids - need to be in edit mode to access edit_bones
        prev = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = self.armature
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        for bone in data.edit_bones:
            if 'OGREID' in bone:
                self.ids[ bone.name ] = bone['OGREID']

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.context.view_layer.objects.active = prev
        self.armature.hide_viewport = self.hidden

        # Allocate bone ids
        index = 0
        missing = []
        self.bones = [None] * len(data.bones)
        #self.bones = []
        for bone in data.bones:
            if bone.name in self.ids:
                self.bones[ self.ids[bone.name] ] = bone
            else:
                missing.append(bone)
        for bone in missing:
            while self.bones[index]:
                index += 1
            self.bones[index] = bone
            self.ids[bone.name] = index

        # calculate bone rest matrices
        rot = Matrix.Rotation(-1.5707963, 4, 'X')   # Rotate to y-up coordinates
        fix = Matrix.Rotation(1.5707963, 4, 'Z')    # Fix bone axis
        fix = fix @ Matrix.Rotation(3.141592653, 4, 'X')
        self.rest = [None] * len(self.bones)
        for i, bone in enumerate(self.bones):
            if bone == None:
                continue

            if bone.parent:
                self.rest[i] = (bone.parent.matrix_local @ fix @ rot).inverted() @ bone.matrix_local @ fix @ rot
            else:
                self.rest[i] = rot @ bone.matrix_local @ fix @ rot
                
            # Change bones list to local structure, due to blender bone structures being cleared if you switch to edit mode again
            self.bones[i] = Bone(bone)
        
    def bone_id( self, name ):
        return self.ids[name]
        
    def verify(self):
        for i,bone in enumerate(self.bones):
            print(i, bone)

    def export_xml( self, doc, root):
        bones = doc.createElement('bones'); root.appendChild( bones )
        bh = doc.createElement('bonehierarchy'); root.appendChild( bh )
        for i,bone in enumerate(self.bones):

            if bone == None:
                continue


            print(i, bone)
        
            b = doc.createElement('bone')
            b.setAttribute('name', bone.name)
            b.setAttribute('id', str(i) )
            bones.appendChild( b )

            if bone.parent:
                bp = doc.createElement('boneparent')
                bp.setAttribute('bone', bone.name)
                bp.setAttribute('parent', bone.parent)
                bh.appendChild( bp )

            mat = self.rest[i]
            pos = doc.createElement( 'position' ); b.appendChild( pos )
            x,y,z = mat.to_translation()
            pos.setAttribute('x', '%6f' %x )
            pos.setAttribute('y', '%6f' %y )
            pos.setAttribute('z', '%6f' %z )

            rot =  doc.createElement( 'rotation' ); b.appendChild( rot )
            q = mat.to_quaternion()
            rot.setAttribute('angle', '%6f' %q.angle )
            axis = doc.createElement('axis'); rot.appendChild( axis )
            x,y,z = q.axis
            axis.setAttribute('x', '%6f' %x )
            axis.setAttribute('y', '%6f' %y )
            axis.setAttribute('z', '%6f' %z )

# -------------------------------------------------------------------- #

def bCollectAnimationData(meshData):
        if 'skeleton' not in meshData: return
        armature = meshData['skeleton'].armature
        animdata = armature.animation_data
        if animdata:
            actions = []
            # Current action
            if animdata.action:
                actions.append(animdata.action)
            # actions in NLA
            if animdata.nla_tracks:
                for track in animdata.nla_tracks.values():
                    for strip in track.strips.values():
                        if strip.action and strip.action not in actions:
                            actions.append(strip.action)

            # Export them all
            scene = bpy.context.scene
            currentFrame = scene.frame_current
            currentAction = animdata.action
            meshData['animations'] = []
            for act in actions:
                print('Action', act.name)
                animdata.action = act
                animation = {}
                animation['keyframes'] = collectAnimationData(armature, act.frame_range, scene.render.fps, scene.frame_step)
                animation['name'] = act.name
                animation['length'] = (act.frame_range[1] - act.frame_range[0]) / scene.render.fps
                meshData['animations'].append(animation)

            animdata.action = currentAction
            scene.frame_set(currentFrame)

def collectAnimationData(armature, frame_range, fps, step=1):
    scene = bpy.context.scene
    start, end = frame_range

    keyframes = {}
    for bone in armature.pose.bones:
        if bone.name.startswith("H_"):
            continue
        keyframes[bone.name] = [[],[],[]]   # pos, rot, scl
    
    fix1 = Matrix([(1,0,0), (0,0,1), (0,-1,0)])		# swap YZ and negate some
    fix2 = Matrix([(0,1,0), (0,0,1), (1,0,0)])	
    
    # Get base matrices
    mat = {}
    hidden = armature.hide_viewport
    armature.hide_viewport = False
    prev = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    for b in armature.data.edit_bones:
        if b.name.startswith("H_"):
            continue
        if b.parent: mat[b.name] = fix2 @ b.parent.matrix.to_3x3().transposed() @ b.matrix.to_3x3()
        else: mat[b.name] = fix1 @  b.matrix.to_3x3()
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.context.view_layer.objects.active = prev
    armature.hide_viewport = hidden
    
    # Reset pose. Kludge to prevent animations overlaying each other when
    # exporting multiple animations - Kindrad
    for poseBone in armature.pose.bones:
        iQ = Quaternion((0,0,0),1)
        poseBone.rotation_quaternion = iQ
        poseBone.scale = Vector((1,1,1))
        poseBone.location = poseBone.bone.head
        
    

    # Collect data
    for frame in range( int(start), int(end)+1, step):
        time = (frame - start) / fps
        bpy.context.scene.frame_set(frame)
        for bone in armature.pose.bones:
            if bone.name.startswith("H_"):
                continue
            loc = bone.location
            rot = bone.rotation_quaternion.normalized()
            scl = bone.scale
            
            # transform transation into parent coordinates
            loc = mat[bone.name] @ loc
            
            keyframes[bone.name][0].append((time, (loc[0], loc[1], loc[2])))
            keyframes[bone.name][1].append((time, (rot[0], rot[1], rot[2], rot[3])))
            keyframes[bone.name][2].append((time, (scl[0], scl[1], scl[2])))

    # Remove unnessesary tracks
    identity = [ (0,0,0), (1,0,0,0), (1,1,1) ]
    for bone, data in keyframes.items():
        for track in range(3):
            used = False
            for key in data[track]:
                if used: break
                for i in range(len(identity[track])):
                    if abs(key[1][i] - identity[track][i]) > 1e-5:
                        used = True
                        break
            if not used:
                data[track] = []

        # Delete whole track if unused
        if not (data[0] or data[1] or data[2]):
            keyframes[bone] = None

    return keyframes


def xSaveAnimations(meshData, xNode, xDoc):
    if 'animations' in meshData:
        animations = xDoc.createElement("animations")
        xNode.appendChild(animations)

        for animation in meshData['animations']:
            xSaveAnimation(animation, xDoc, animations)


def xSaveAnimation(animation, xDoc, xAnimations):
    anim = xDoc.createElement('animation')
    tracks = xDoc.createElement('tracks')
    xAnimations.appendChild( anim )
    anim.appendChild(tracks)
    anim.setAttribute('name', animation['name'])
    anim.setAttribute('length', '%6f' % animation['length'])
    keyframes = animation['keyframes']
    for bone, data in keyframes.items():
        if not data: continue
        track = xDoc.createElement('track')
        keyframes = xDoc.createElement('keyframes')
        track.setAttribute('bone', bone)
        tracks.appendChild( track )
        track.appendChild( keyframes )

        basis = 0 if data[0] else 1 if data[1] else 2

        for frame in range(len(data[basis])):
            keyframe = xDoc.createElement('keyframe')
            keyframes.appendChild(keyframe)
            keyframe.setAttribute('time', '%6f' % data[basis][frame][0])

            if data[0]:
                loc = data[0][frame][1]
                translate = xDoc.createElement('translate')
                translate.setAttribute('x', '%6f' % loc[0])
                translate.setAttribute('y', '%6f' % loc[1])
                translate.setAttribute('z', '%6f' % loc[2])
                keyframe.appendChild(translate)

            if data[1]:
                rot = data[1][frame][1]
                angle = math.acos(rot[0]) * 2
                l = math.sqrt( rot[1]*rot[1] + rot[2]*rot[2] + rot[3]*rot[3] )
                axis = (1,0,0) if l==0 else (rot[1]/l, rot[2]/l, rot[3]/l)

                rotate = xDoc.createElement('rotate')
                raxis = xDoc.createElement('axis')
                rotate.setAttribute('angle', '%6f' % angle)
                raxis.setAttribute('x', '%6f' % axis[1])
                raxis.setAttribute('y', '%6f' % axis[2])
                raxis.setAttribute('z', '%6f' % axis[0])
                keyframe.appendChild(rotate)
                rotate.appendChild(raxis)

            if data[2]:
                scl = data[2][frame][1]
                scale = xDoc.createElement('scale')
                scale.setAttribute('x', '%6f' % scl[0])
                scale.setAttribute('y', '%6f' % scl[1])
                scale.setAttribute('z', '%6f' % scl[2])
                keyframe.appendChild(scale)


#########################################
def fileExist(filepath):
    try:
        filein = open(filepath)
        filein.close()
        return True
    except:
        print ("No file: ", filepath)
        return False

def toFmtStr(number):
    #return str("%0.7f" % number)
    return str(round(number, 7))

def indent(indent):
    """Indentation.

       @param indent Level of indentation.
       @return String.
    """
    return "        "*indent

def xSaveGeometry(geometry, xDoc, xMesh, isShared):
    # I guess positions (vertices) must be there always
    vertices = geometry['positions']

    if isShared:
        geometryType = "sharedgeometry"
    else:
        geometryType = "geometry"

    isNormals = False
    if 'normals' in geometry:
        isNormals = True
        normals = geometry['normals']

    isTexCoordsSets = False
    texCoordSets = geometry['texcoordsets']
    if texCoordSets>0 and 'uvsets' in geometry:
        isTexCoordsSets = True
        uvSets = geometry['uvsets']

    isColours = False
    if 'colours' in geometry:
        isColours = True
        colours = geometry['colours']

    isTangents = False
    if 'tangents' in geometry:
        isTangents = True
        tangents = geometry['tangents']
    isParity = isTangents and geometry['parity']

    isBinormals = False
    if 'binormals' in geometry:
        isBinormals = True
        binormals = geometry['binormals']


    xGeometry = xDoc.createElement(geometryType)
    xGeometry.setAttribute("vertexcount", str(len(vertices)))
    xMesh.appendChild(xGeometry)

    xVertexBuffer = xDoc.createElement("vertexbuffer")
    xVertexBuffer.setAttribute("positions", "true")
    if isNormals:
        xVertexBuffer.setAttribute("normals", "true")
    if isTexCoordsSets:
        xVertexBuffer.setAttribute("texture_coord_dimensions_0", "2")
        xVertexBuffer.setAttribute("texture_coords", "1") #str(texCoordSets)) # Only export one set

    if isColours:
        xVertexBuffer.setAttribute("colours_diffuse", "true")
    if isTangents:
        xVertexBuffer.setAttribute("tangents", "true")
        if isParity: xVertexBuffer.setAttribute("tangent_dimensions", "4")
    if isBinormals:
        xVertexBuffer.setAttribute("binormals", "true")

    xGeometry.appendChild(xVertexBuffer)

    for i, vx in enumerate(vertices):
        xVertex = xDoc.createElement("vertex")
        xVertexBuffer.appendChild(xVertex)
        xPosition = xDoc.createElement("position")
        xPosition.setAttribute("x", toFmtStr(vx[0]))
        xPosition.setAttribute("y", toFmtStr(vx[2]))
        xPosition.setAttribute("z", toFmtStr(-vx[1]))
        xVertex.appendChild(xPosition)

        if isNormals:
            xNormal = xDoc.createElement("normal")
            xNormal.setAttribute("x", toFmtStr(normals[i][0]))
            xNormal.setAttribute("y", toFmtStr(normals[i][2]))
            xNormal.setAttribute("z", toFmtStr(-normals[i][1]))
            xVertex.appendChild(xNormal)

        if isTexCoordsSets:
            xUVSet = xDoc.createElement("texcoord")
            xUVSet.setAttribute("u", toFmtStr(uvSets[i][0][0])) # take only 1st set for now
            xUVSet.setAttribute("v", toFmtStr(1.0 - uvSets[i][0][1]))
            xVertex.appendChild(xUVSet)

        if isColours:
            xColour = xDoc.createElement("colour_diffuse")
            xColour.setAttribute("value", '%g %g %g %g' % (colours[i][0], colours[i][1], colours[i][2], colours[i][3]))
            xVertex.appendChild(xColour)

        if isTangents:
            xTangent = xDoc.createElement("tangent")
            xTangent.setAttribute("x", toFmtStr(tangents[i][0]))
            xTangent.setAttribute("y", toFmtStr(tangents[i][2]))
            xTangent.setAttribute("z", toFmtStr(-tangents[i][1]))
            if isParity: xTangent.setAttribute("w", toFmtStr(tangents[i][3]))
            xVertex.appendChild(xTangent)

        if isBinormals:
            xBinormal = xDoc.createElement("binormal")
            xBinormal.setAttribute("x", toFmtStr(binormals[i][0]))
            xBinormal.setAttribute("y", toFmtStr(binormals[i][2]))
            xBinormal.setAttribute("z", toFmtStr(-binormals[i][1]))
            xVertex.appendChild(xBinormal)


def xSaveSubMeshes(meshData, xDoc, xMesh, hasSharedGeometry):

    xSubMeshes = xDoc.createElement("submeshes")
    xMesh.appendChild(xSubMeshes)

    for submesh in meshData['submeshes']:

        numVerts = len(submesh['geometry']['positions'])

        xSubMesh = xDoc.createElement("submesh")
        xSubMesh.setAttribute("material", submesh['material'])
        if hasSharedGeometry:
            xSubMesh.setAttribute("usesharedvertices", "true")
        else:
            xSubMesh.setAttribute("usesharedvertices", "false")
        xSubMesh.setAttribute("use32bitindexes", str(bool(numVerts > 65535)))
        xSubMesh.setAttribute("operationtype", "triangle_list")
        xSubMeshes.appendChild(xSubMesh)
        # write all faces
        if 'faces' in submesh:
            faces = submesh['faces']
            xFaces = xDoc.createElement("faces")
            xFaces.setAttribute("count", str(len(faces)))
            xSubMesh.appendChild(xFaces)
            for face in faces:
                xFace = xDoc.createElement("face")
                xFace.setAttribute("v1", str(face[0]))
                xFace.setAttribute("v2", str(face[1]))
                xFace.setAttribute("v3", str(face[2]))
                xFaces.appendChild(xFace)
        # if there is geometry per sub mesh
        if 'geometry' in submesh:
            geometry = submesh['geometry']
            xSaveGeometry(geometry, xDoc, xSubMesh, hasSharedGeometry)
        # boneassignments
        if 'skeleton' in meshData:
            skeleton = meshData['skeleton']
            xBoneAssignments = xDoc.createElement("boneassignments")
            for vxIdx, vxBoneAsg in enumerate(submesh['geometry']['boneassignments']):
                for boneAndWeight in vxBoneAsg:
                    boneName = boneAndWeight[0]
                    boneWeight = boneAndWeight[1]
                    xVxBoneassignment = xDoc.createElement("vertexboneassignment")
                    xVxBoneassignment.setAttribute("vertexindex", str(vxIdx))
                    xVxBoneassignment.setAttribute("boneindex", str(skeleton.bone_id(boneName)))
                    xVxBoneassignment.setAttribute("weight", '%6f' % boneWeight)
                    xBoneAssignments.appendChild(xVxBoneassignment)
            xSubMesh.appendChild(xBoneAssignments)

def xSavePoses(meshData, xDoc, xMesh):
    xPoses = xDoc.createElement("poses")
    xMesh.appendChild(xPoses)
    for index, submesh in enumerate(meshData['submeshes']):
        if not submesh['poses']: continue
        for name in submesh['poses']:
            xPose = xDoc.createElement("pose")
            xPose.setAttribute('target', 'submesh')
            xPose.setAttribute('index', str(index))
            xPose.setAttribute('name', name)
            xPoses.appendChild(xPose)
            pose = submesh['poses'][name]
            for v in pose:
                xPoseVertex = xDoc.createElement('poseoffset')
                xPoseVertex.setAttribute('index', str(v[0]))
                xPoseVertex.setAttribute('x', '%6f' %  v[1] )
                xPoseVertex.setAttribute('y', '%6f' %  v[3] )
                xPoseVertex.setAttribute('z', '%6f' % -v[2] )
                xPose.appendChild(xPoseVertex)

def xSaveSkeletonData(blenderMeshData, filepath):
    from xml.dom.minidom import Document

    if 'skeleton' in blenderMeshData:
        skeleton = blenderMeshData['skeleton']

        xDoc = Document()
        xRoot = xDoc.createElement("skeleton")
        xDoc.appendChild(xRoot)
        skeleton.export_xml(xDoc, xRoot)

        if 'animations' in blenderMeshData:
            xSaveAnimations(blenderMeshData, xRoot, xDoc)

        #xmlfile = os.path.join(filepath, '%s.skeleton.xml' %name )
        nameOnly = os.path.splitext(filepath)[0] # removing .mesh
        xmlfile = nameOnly + ".skeleton.xml"
        data = xDoc.toprettyxml(indent='    ')
        f = open( xmlfile, 'wb' )
        f.write( bytes(data,'utf-8') )
        f.close()


def xSaveMeshData(meshData, filepath, export_skeleton):
    from xml.dom.minidom import Document

    hasSharedGeometry = False
    if 'sharedgeometry' in meshData:
        hasSharedGeometry = True

    # Create the minidom document
    print("Creating " + filepath + ".xml")
    xDoc = Document()

    xMesh = xDoc.createElement("mesh")
    xDoc.appendChild(xMesh)

    if hasSharedGeometry:
        geometry = meshData['sharedgeometry']
        xSaveGeometry(geometry, xDoc, xMesh, hasSharedGeometry)

    xSaveSubMeshes(meshData, xDoc, xMesh, hasSharedGeometry)

    if 'has_poses' in meshData:
        xSavePoses(meshData, xDoc, xMesh)

    #skeleton link only
    if 'skeleton' in meshData:
        xSkeletonlink = xDoc.createElement("skeletonlink")
        # default skeleton
        linkSkeletonName = meshData['skeleton'].name
        if(export_skeleton):
            nameDotMeshDotXml = os.path.split(filepath)[1].lower()
            nameDotMesh = os.path.splitext(nameDotMeshDotXml)[0]
            linkSkeletonName = os.path.splitext(nameDotMesh)[0]
        #xSkeletonlink.setAttribute("name", meshData['skeleton']['name']+".skeleton")
        xSkeletonlink.setAttribute("name", linkSkeletonName+".skeleton")
        xMesh.appendChild(xSkeletonlink)

    # Print our newly created XML
    fileWr = open(filepath + ".xml", 'w')
    fileWr.write(xDoc.toprettyxml(indent="    ")) # 4 spaces
    fileWr.close()

def xSaveMaterialData(filepath, meshData, overwriteMaterialFlag, copyTextures):
    if 'materials' not in meshData: return
    allMatData = meshData['materials']

    if len(allMatData) <= 0:
        print('Mesh has no materials')
        return

    matFile = os.path.splitext(filepath)[0] # removing .mesh
    matFile = matFile + ".material"
    print("material file: %s" % matFile)
    isMaterial = os.path.isfile(matFile)

    # if is no material file, or we are forced to overwrite it, write the material file
    if isMaterial==False or overwriteMaterialFlag==True:
        # write material
        fileWr = open(matFile, 'w')
        for matName, matInfo in allMatData.items():
            fileWr.write("material %s\n" % matName)
            fileWr.write("{\n")
            fileWr.write(indent(1) + "technique\n" + indent(1) + "{\n")
            fileWr.write(indent(2) + "pass\n" + indent(2) + "{\n")

            # write material content here
            fileWr.write(indent(3) + "ambient %f %f %f\n" % (matInfo['ambient'][0], matInfo['ambient'][1], matInfo['ambient'][2]))
            fileWr.write(indent(3) + "diffuse %f %f %f\n" % (matInfo['diffuse'][0], matInfo['diffuse'][1], matInfo['diffuse'][2]))
            fileWr.write(indent(3) + "specular %f %f %f 0\n" % (matInfo['specular'][0], matInfo['specular'][1], matInfo['specular'][2]))
            fileWr.write(indent(3) + "emissive %f %f %f\n" % (matInfo['emissive'][0], matInfo['emissive'][1], matInfo['emissive'][2]))

            if 'texture' in matInfo:
                fileWr.write(indent(3) + "texture_unit\n" + indent(3) + "{\n")
                fileWr.write(indent(4) + "texture %s\n" % matInfo['texture'])
                fileWr.write(indent(3) + "}\n") # texture unit

            fileWr.write(indent(2) + "}\n") # pass
            fileWr.write(indent(1) + "}\n") # technique
            fileWr.write("}\n")

        fileWr.close()


    #try to copy material textures to destination
    if copyTextures:
        for matName, matInfo in allMatData.items():
            if 'texture' in matInfo:
                if 'texture_path' in matInfo:
                    srcTextureFile = matInfo['texture_path']
                    baseDirName = os.path.dirname(bpy.data.filepath)
                    if (srcTextureFile[0:2] == "//"):
                        print("Converting relative image name \"%s\"" % srcTextureFile)
                        srcTextureFile = os.path.join(baseDirName, srcTextureFile[2:])
                    if fileExist(srcTextureFile):
                        # copy texture to dir
                        print("Copying texture \"%s\"" % srcTextureFile)
                        try:
                            print(" to \"%s\"" % os.path.dirname(matFile))
                            shutil.copy(srcTextureFile, os.path.dirname(matFile))
                        except:
                            print("Error copying \"%s\"" % srcTextureFile)
                    else:
                        print("Can't copy texture \"%s\" because file does not exists!" % srcTextureFile)



def getVertexIndex(vertexInfo, vertexList):

    for vIdx, vert in enumerate(vertexList):
        if vertexInfo == vert:
            return vIdx

    #not present in list:
    vertexList.append(vertexInfo)
    return len(vertexList)-1

# Convert rgb colour to brightness value - used for alpha channel
def luminosity(c):
    return c[0] * 0.25 + c[1] * 0.5 + c[2] * 0.25

def bCollectMeshData(meshData, selectedObjects, applyModifiers, exportColour, exportTangents, exportBinormals, exportPoses):
    import bmesh
    subMeshesData = []
    for ob in selectedObjects:
        subMeshData = {}
        #ob = bpy.types.Object ##
        materialName = ob.name
        for m in ob.data.materials:
            if m: materialName = m.name
        
        #mesh = bpy.types.Mesh ##
        tobj = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()) if applyModifiers else ob
        mesh = tobj.to_mesh()
        
        # use bmesh to triangulate
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        
        # Calculate normals and tangents
        if not mesh.uv_layers.active: exportTangents = exportBinormals = False
        if exportTangents:
            mesh.calc_tangents(uvmap = mesh.uv_layers.active.name)
        else:
            mesh.calc_normals_split()

        # pick uv data
        uvData = mesh.uv_layers.active.data if mesh.uv_layers.active else None

        # Pick colour data
        colourData = None
        alphaData = None
        if mesh.vertex_colors.active and exportColour:
            colourData = mesh.vertex_colors.active.data
            for layer in mesh.vertex_colors:
                if layer.name.lower() == 'alpha':
                    alphaData = layer.data
                    # pick a different one for colour if alpha layer is active
                    if layer.active:
                        colourData = None
                        for layer in mesh.vertex_colors:
                            if not layer.active:
                                colourData = layer.data
                                break
                    break


        vertexList = []
        newFaces = []
        map = {}

        import sys
        progressScale = 1.0 / (len(mesh.polygons) - 1)
        for fidx, face in enumerate(mesh.polygons):
            tris = []
            tris.append( (face.vertices[0], face.vertices[1], face.vertices[2]) )
            if(len(face.vertices)>=4):
                tris.append( (face.vertices[0], face.vertices[2], face.vertices[3]) )
            if SHOW_EXPORT_TRACE_VX:
                print("_face: "+ str(fidx) + " indices [" + str(list(face.vertices))+ "]")
            
            # Progress
            percent = fidx * progressScale
            sys.stdout.write( "\rVertices [" + '=' * int(percent*50) + '>' + '.' * int(50-percent*50) + "] " + str(int(percent*10000)/100.0) + "%   ")
            sys.stdout.flush()
            
            # should be triangles
            if len(face.vertices) != 3:
                raise ValueError('Polygon not a triangle')
            

            # Add triangle
            newFaceVx = []
            for i in range(3):
                vertex = face.vertices[i]
                loop = face.loop_indices[i];
                
                px, py, pz = mesh.vertices[vertex].co
                nx, ny, nz = mesh.loops[loop].normal
                u, v  = uvData[loop].uv if uvData else (0, 0)
                r,g,b,a = colourData[loop].color if colourData else (1,1,1,1)
                a = alphaData[loop].color[0] if alphaData else 1
                
                tangent = mesh.loops[loop].tangent[:] + (mesh.loops[loop].bitangent_sign,) if exportTangents else None
                binormal =  mesh.loops[loop].bitangent * -1 if exportBinormals else None
                
                #vertex groups
                boneWeights = {}
                for vxGroup in mesh.vertices[vertex].groups:
                    if vxGroup.weight > 0.01:
                        vg = ob.vertex_groups[ vxGroup.group ]
                        boneWeights[vg.name] = vxGroup.weight
                
                # Add vertex
                vert = VertexInfo(px,py,pz, nx,ny,nz, u,v, r,g,b,a, boneWeights, vertex, tangent, binormal)
                newVxIdx = map.get(vert)
                if newVxIdx == None:
                    newVxIdx = len(vertexList)
                    vertexList.append(vert)
                    map[vert] = newVxIdx;
                newFaceVx.append(newVxIdx)
            
            newFaces.append(newFaceVx)
        
        # geometry
        geometry = {}
        faces = []
        normals = []
        tangents = []
        binormals = []
        positions = []
        uvTex = []
        colours = []
        #vertex groups of object
        boneAssignments = []
        faces = newFaces
        needsParity = False

        for vxInfo in vertexList:
            positions.append([vxInfo.px, vxInfo.py, vxInfo.pz])
            normals.append([vxInfo.nx, vxInfo.ny, vxInfo.nz])
            uvTex.append([[vxInfo.u, vxInfo.v]])
            colours.append([vxInfo.r, vxInfo.g, vxInfo.b, vxInfo.a])
        
            boneWeights = []
            for boneW in vxInfo.boneWeights.keys():
                boneWeights.append([boneW, vxInfo.boneWeights[boneW]])
            boneAssignments.append(boneWeights)
        
        if exportTangents:
            for vxInfo in vertexList:
                tangents.append(vxInfo.tangent)
                binormals.append(vxInfo.binormal)

            if not exportBinormals:
                for vxInfo in vertexList:
                    if vxInfo.tangent[3]<0:
                        needsParity=True
                        break;


        if SHOW_EXPORT_TRACE_VX:
            print("uvTex:")
            print(uvTex)
            print("boneAssignments:")
            print(boneAssignments)


        # Shape keys - poses
        poses = None
        if exportPoses and mesh.shape_keys and mesh.shape_keys.key_blocks:
            poses = {}
            for pose in mesh.shape_keys.key_blocks:
                if pose.relative_key:
                    poseData = []
                    for index, v in enumerate(vertexList):
                        base = pose.relative_key.data[ v.original ].co
                        pos = pose.data[ v.original ].co
                        x = pos[0] - base[0]
                        y = pos[1] - base[1]
                        z = pos[2] - base[2]
                        if x!=0 or y!=0 or z!=0:
                            poseData.append( (index, x, y, z) )
                    if poseData:
                        poses[pose.name] = poseData


        geometry['positions'] = positions
        geometry['normals'] = normals
        geometry['texcoordsets'] = len(mesh.uv_layers)
        if SHOW_EXPORT_TRACE:
            print("texcoordsets: " + str(len(mesh.uv_layers)))
        if uvData:
            geometry['uvsets'] = uvTex
        if colourData or alphaData:
            geometry['colours'] = colours
        if exportTangents:
            geometry['tangents'] = tangents
            geometry['parity'] = needsParity
        if exportBinormals:
            geometry['binormals'] = binormals

        #need bone name to bone ID dict
        geometry['boneassignments'] = boneAssignments

        subMeshData['material'] = materialName
        subMeshData['faces'] = faces
        subMeshData['geometry'] = geometry
        subMeshData['poses' ] = poses
        subMeshesData.append(subMeshData)

        if poses: meshData['has_poses'] = True

        # Clear temporary mesh data
        tobj.to_mesh_clear()

    meshData['submeshes']=subMeshesData

    return meshData

def bCollectSkeletonData(blenderMeshData, selectedObjects):
    if SHOW_EXPORT_TRACE:
        print("bpy.data.armatures = %s" % bpy.data.armatures)

    # TODO, for now just take armature of first selected object
    if selectedObjects[0].find_armature():
        # creates and parses blender skeleton
        skeleton = Skeleton( selectedObjects[0] )
        blenderMeshData['skeleton'] = skeleton

def bCollectMaterialData(blenderMeshData, selectedObjects):

    allMaterials = {}
    blenderMeshData['materials'] = allMaterials

    for ob in selectedObjects:
        if ob.type == 'MESH' and len(ob.data.materials)>0:
            for mat in ob.data.materials:
                #mat = bpy.types.Material ##
                if mat and mat.name not in allMaterials:
                    matInfo = {}
                    allMaterials[mat.name]=matInfo
                    # ambient
                    matInfo['ambient']=[ mat.ambient, mat.ambient, mat.ambient]
                    # diffuse
                    matInfo['diffuse']=[mat.diffuse_color[0],mat.diffuse_color[1],mat.diffuse_color[2]]
                    # specular
                    matInfo['specular']=[mat.specular_color[0],mat.specular_color[1],mat.specular_color[2]]
                    # emissive
                    matInfo['emissive']=[mat.emit,mat.emit,mat.emit]
                    # texture
                    if len(mat.texture_slots)>0:
                        for slot in mat.texture_slots:
                            if slot and slot.texture.type == 'IMAGE' and slot.texture.image:
                                matInfo['texture'] = slot.texture.image.name
                                matInfo['texture_path'] = slot.texture.image.filepath
                                break


def XMLtoOGREConvert(blenderMeshData, filepath, ogreXMLconverter,
                     export_skeleton, keep_xml):

    if ogreXMLconverter is None: return False

    # for mesh
    # use Ogre XML converter  xml -> binary mesh
    try:
        xmlFilepath = filepath + ".xml"
        subprocess.call([ogreXMLconverter, xmlFilepath])
        # remove XML file if successfully converted
        if keep_xml is False and os.path.isfile(filepath):
            os.unlink("%s" % xmlFilepath)

        if 'skeleton' in blenderMeshData and export_skeleton:
            # for skeleton
            skelFile = os.path.splitext(filepath)[0] # removing .mesh
            xmlFilepath = skelFile + ".skeleton.xml"
            subprocess.call([ogreXMLconverter, xmlFilepath])
            # remove XML file
            if keep_xml is False:
                os.unlink("%s" % xmlFilepath)

        return True

    except:
        print("Error: Could not run", ogreXMLconverter)
        return False

def save(operator, context, filepath,
         xml_converter=None,
         keep_xml=False,
         export_tangents=False,
         export_binormals=False,
         export_colour=False,
         tangent_parity=False,
         apply_transform=True,
         apply_modifiers=True,
         export_materials=False,
         overwrite_material=False,
         copy_textures=False,
         export_skeleton=False,
         export_poses=False,
         export_animation=False,
         batch_export=False,
         ):

    global blender_version

    blender_version = bpy.app.version[0]*100 + bpy.app.version[1]
    if(not batch_export):

        # just check if there is extension - .mesh
        if '.mesh' not in filepath.lower():
            filepath = filepath + ".mesh"

        print("saving...")
        print(str(filepath))


        # get mesh data from selected objects
        selectedObjects = []
        scn = bpy.context.view_layer
        for ob in scn.objects:
            if ob.select_get() and ob.type!='ARMATURE':
                selectedObjects.append(ob)

        if len(selectedObjects)==0:
            print("No objects selected for export.")
            operator.report( {'WARNING'}, "No objects selected for export")
            return {'CANCELLED'}


        # go to the object mode
        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')


        # apply transform
        if apply_transform:
            bpy.ops.object.transform_apply(rotation=True, scale=True)


        # Save Mesh
        blenderMeshData = {}

        #skeleton
        bCollectSkeletonData(blenderMeshData, selectedObjects)
        #mesh
        bCollectMeshData(blenderMeshData, selectedObjects, apply_modifiers, export_colour, export_tangents, export_binormals, export_poses)
        #materials
        if export_materials:
            bCollectMaterialData(blenderMeshData, selectedObjects)

        if export_animation:
            bCollectAnimationData(blenderMeshData)

        if SHOW_EXPORT_TRACE:
            print(blenderMeshData['materials'])

        if SHOW_EXPORT_DUMPS:
            dumpFile = filepath + ".EDump"
            fileWr = open(dumpFile, 'w')
            fileWr.write(str(blenderMeshData))
            fileWr.close()

        if export_skeleton:
            xSaveSkeletonData(blenderMeshData, filepath)

        xSaveMeshData(blenderMeshData, filepath, export_skeleton)

        xSaveMaterialData(filepath, blenderMeshData, overwrite_material, copy_textures)

        if not XMLtoOGREConvert(blenderMeshData, filepath, xml_converter, export_skeleton, keep_xml):
            operator.report( {'WARNING'}, "Failed to convert .xml files to .mesh")
    else:

         # just check if there is extension - .mesh
        #if '.mesh' not in filepath.lower():
            #filepath = filepath + ".mesh"
        directory = os.path.dirname(filepath)


        # get mesh data from selected objects
        selectedObjects = []
        scn = bpy.context.view_layer
        for ob in scn.objects:
            if ob.select_get() and ob.type!='ARMATURE':
                selectedObjects.append(ob)

        if len(selectedObjects)==0:
            print("No objects selected for export.")
            operator.report( {'WARNING'}, "No objects selected for export")
            return {'CANCELLED'}


        # go to the object mode
        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')




        for obj in selectedObjects:

            selectedObj = []
            selectedObj.append(obj)

            filepath = directory + "\\" + obj.name + ".mesh"

            print("saving...")
            print(str(filepath))

            # apply transform
            if apply_transform:
                bpy.ops.object.transform_apply(rotation=True, scale=True)


            # Save Mesh
            blenderMeshData = {}

            #skeleton
            bCollectSkeletonData(blenderMeshData, selectedObj)
            #mesh
            bCollectMeshData(blenderMeshData, selectedObj, apply_modifiers, export_colour, export_tangents, export_binormals, export_poses)
            #materials
            if export_materials:
                bCollectMaterialData(blenderMeshData, selectedObj)

            if export_animation:
                bCollectAnimationData(blenderMeshData)

            if SHOW_EXPORT_TRACE:
                print(blenderMeshData['materials'])

            if SHOW_EXPORT_DUMPS:
                dumpFile = filepath + ".EDump"
                fileWr = open(dumpFile, 'w')
                fileWr.write(str(blenderMeshData))
                fileWr.close()

            if export_skeleton:
                xSaveSkeletonData(blenderMeshData, filepath)

            xSaveMeshData(blenderMeshData, filepath, export_skeleton)

            xSaveMaterialData(filepath, blenderMeshData, overwrite_material, copy_textures)

            if not XMLtoOGREConvert(blenderMeshData, filepath, xml_converter, export_skeleton, keep_xml):
                operator.report( {'WARNING'}, "Failed to convert .xml files to .mesh")


    print("done.")

    return {'FINISHED'}

