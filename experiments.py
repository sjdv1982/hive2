import bge
import mathutils 
from PIL import Image
from bge import texture
from bge import logic
from mathutils import Vector
from bgl import Buffer, GL_BYTE


def cmp(a, b): 
    return int((a > b) -(a < b))


def main(cont):
    own = cont.owner

    MOA = cont.sensors['MouseOverAny']
    Left = cont.sensors['Mouse']
    MOA2 = cont.sensors['MouseOverColor']
    MOA3 = cont.sensors['MOA3']
    

    if 'Init' not in own:
        for child in own.children:
            if 'T1' in child:
                own['T1']=child
            if 'T2' in child:
                own['T2']=child

        own['Camera']=bge.logic.getCurrentScene().objects['Camera']
        meshOb = bge.logic.getCurrentScene().objects['Plane']
        
        
        ####replace canvas texture with file#####
        obj = meshOb
        
        
        own['Init']=True
        
        mesh = meshOb.meshes[0]
        VL =[]
        PL =[]
        #### Build BVHTREE ######
        for m_index in range(len(mesh.materials)):
            for v_index in range(mesh.getVertexArrayLength(m_index)):
                vertex = mesh.getVertex(m_index, v_index)
                xYz = meshOb.worldPosition+(meshOb.worldOrientation.inverted()*vertex.XYZ)
                
                VL.append((xYz[0],xYz[1],xYz[2]) )
                
                
            for f_index in range(mesh.numPolygons):
                poly = mesh.getPolygon(f_index)
                L=[]
                v0 = poly.getVertexIndex(0)
                L.append(v0)
                v1 = poly.getVertexIndex(1)
                L.append(v1)
                v2 = poly.getVertexIndex(2)
                L.append(v2)
                if poly.v4:
                    v3=poly.getVertexIndex(3)
                    L.append(v3)
                PL.append(L)
                    
        
        own['Mesh']=mesh     
        own['OB'] = obj   
        B =mathutils.bvhtree.BVHTree.FromPolygons(VL, PL, all_triangles=False, epsilon=0.0)
        
        own['BVH']=B
    
    if MOA3.positive and Left.positive:
        v2 = MOA3.hitPosition-own.worldPosition

        ray =  own.rayCast(own.worldPosition+v2*300, own.worldPosition,0,'',0,0,2)
        #swapped BVHTree for reg game engine raycast with polyProxy2 (return uv)

        
        if ray[3]:
            obj = own['OB']
            mesh = own['Mesh']
            hitPosition = MOA3.hitPosition
           
            # calculate vectors from point hitPoint to vertices p1, p2 and p3:
            poly = ray[3] # hit face from ray
            #print(poly.v1)
            
            vertex_a = mesh.getVertex(0, poly.v1)
            vertex_b = mesh.getVertex(0, poly.v2)
            vertex_c = mesh.getVertex(0, poly.v3)
           
            hitPosition = MOA3.hitPosition
           
            marker = obj.scene.addObject('HL',own,1)
            marker.worldPosition = hitPosition
           
             # find the uv corresponding to point f (uv1/uv2/uv3 are associated to p1/p2/p3)
            obj_space_pos = obj.worldTransform.inverted() * MOA3.hitPosition
            uv= mathutils.geometry.barycentric_transform(obj_space_pos, vertex_a.XYZ, vertex_b.XYZ, vertex_c.XYZ,                              vertex_a.UV.to_3d(), vertex_b.UV.to_3d(), vertex_c.UV.to_3d())

            own['UV']=str(uv)
            own['T1']['Text']=str(uv[0])
            own['T2']['Text']=str(uv[1])

            # we have UV lets draw!
            # if 'IM' not in own:
            #     own['IM']=Image.open(logic.expandPath("//NewImage.png"))
            #     own['Brush']=Image.open(logic.expandPath("//RedBrush.png"))
            #
            # print(own['Brush'].size)
            # background = own['IM']
            # foreground = own['Brush']
            #
            # background.paste(foreground, (int(uv[0]*background.width), int(uv[1]*background.width)), foreground)
            #
            # print(background.size)
            # background.save(logic.expandPath("//newSavedImage.png"))
            surface = own['OB']

            from struct import pack
            width, height = 32, 32

            colours = [255, 0, 0] * width * height
            img_data = pack("{}B".format(len(colours)), *colours)

            # imbuf = Buffer(GL_BYTE, len(img_data), img_data)
            # surface_texture = surface['_texture'] = texture.Texture(surface, 0)
            # surface_texture.source = texture.ImageBuff()
            # surface_texture.source.load(imbuf, width, height)
            # surface_texture.refresh(True)

            # object_texture = texture.Texture(own['OB'], 0)
            # url = logic.expandPath("//newSavedImage.png")
            # new_source = texture.ImageFFmpeg(url)
            # print(new_source.size)
            # logic.texture = object_texture
            # logic.texture.source = new_source
            # logic.texture.refresh(True)

    if MOA.positive:
        added=bge.logic.getCurrentScene().addObject('HL',own,1)
        added.worldPosition=MOA.hitObject.worldPosition
        added.worldPosition.z+=.01
        
        if Left.positive:
            #color a whole object
            pass
            #MOA.hitObject.color = [ own['R'], own['G'], own['B'],own['A']]

    if MOA2.positive and Left.positive:
        # snag color from a object
        
        own['R']=MOA2.hitObject.color[0]
        own['G']=MOA2.hitObject.color[1]
        own['B']=MOA2.hitObject.color[2]
        own['A']=MOA2.hitObject.color[3]

