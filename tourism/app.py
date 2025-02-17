import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import rdflib
import os

app = Flask(__name__)
CORS(app)

IMG_FOLDER = 'img'  
app.config['IMG_FOLDER'] = IMG_FOLDER

# โหลด OWL ไฟล์
g = rdflib.Graph()
g.parse("mytourism.owl", format="xml")

# ฟังก์ชันดึงรายชื่อจังหวัดทั้งหมดจากฐานข้อมูล RDF
def get_all_province_names():
    query = """
    PREFIX my: <http://www.my_ontology.edu/mytourism#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT ?name
    WHERE {
        ?province rdf:type my:ThaiProvince ;
                  my:hasNameOfProvince ?name .
    }
    """
    results = g.query(query)
    return {row.name.toPython().strip().lower().replace(" ", ""): row.name.toPython() for row in results if row.name}

# โหลดรายชื่อจังหวัดทั้งหมด (เป็น dict: {ชื่อจังหวัดในรูปแบบ lowercase ไม่มีช่องว่าง : ชื่อจังหวัดจริง})
province_names_dict = get_all_province_names()

# ฟังก์ชันค้นหาจังหวัดแบบไม่สนใจตัวพิมพ์และช่องว่าง
def get_province_data(province_name, lang="th"):
    # ทำให้ชื่อที่ป้อนมาเป็นตัวพิมพ์เล็กและไม่มีช่องว่าง
    normalized_input = province_name.strip().lower().replace(" ", "")

    # ตรวจสอบว่ามีชื่อจังหวัดที่ตรงกันหรือไม่
    if normalized_input not in province_names_dict:
        return {"message": "ไม่พบข้อมูลจังหวัดนี้" if lang == "th" else "No data found for this province"}

    # ใช้ชื่อจังหวัดที่ตรงกันจริงๆ จากฐานข้อมูล RDF
    correct_province_name = province_names_dict[normalized_input]

    query = """
    PREFIX my: <http://www.my_ontology.edu/mytourism#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT ?name ?motto ?flower ?tree ?url ?latitude ?longitude ?img ?seal ?traditional_name
    WHERE {
        ?province rdf:type my:ThaiProvince ;
                  my:hasNameOfProvince ?name .

        OPTIONAL { ?province my:hasMotto ?motto . FILTER (lang(?motto) = "%s") }
        OPTIONAL { ?province my:hasFlower ?flower . FILTER (lang(?flower) = "%s") }
        OPTIONAL { ?province my:hasTree ?tree . FILTER (lang(?tree) = "%s") }
        OPTIONAL { ?province my:hasURLOfProvince ?url . }
        OPTIONAL { ?province my:hasLatitudeOfProvince ?latitude . }
        OPTIONAL { ?province my:hasLongitudeOfProvince ?longitude . }
        OPTIONAL { ?province my:hasImageOfProvince ?img . }
        OPTIONAL { ?province my:hasSeal ?seal . FILTER (lang(?seal) = "%s") }
        OPTIONAL { ?province my:hasTraditionalNameOfProvince ?traditional_name . FILTER (lang(?traditional_name) = "%s") }

        FILTER (str(?name) = "%s" || ?name = "%s"@th || ?name = "%s"@en)
    }
    """ % (lang, lang, lang, lang, lang, correct_province_name, correct_province_name, correct_province_name)

    results = g.query(query)

    province_data = {
        "province": correct_province_name,  # ใช้ชื่อจังหวัดจริงจากฐานข้อมูล
        "motto": "",
        "flower": "",
        "tree": "",
        "url": "",
        "latitude": "",
        "longitude": "",
        "img": "",
        "seal": "",  # เพิ่มข้อมูล seal
        "traditional_names": []
    }

    for row in results:
        if row.motto:
            province_data["motto"] = row.motto.toPython()
        if row.flower:
            province_data["flower"] = row.flower.toPython()
        if row.tree:
            province_data["tree"] = row.tree.toPython()
        if row.url:
            province_data["url"] = row.url.toPython()
        if row.latitude:
            province_data["latitude"] = float(row.latitude.toPython())
        if row.longitude:
            province_data["longitude"] = float(row.longitude.toPython())
        if row.img:
            province_data["img"] = row.img.toPython()
        if row.seal:
            province_data["seal"] = row.seal.toPython()  # เพิ่มข้อมูล seal
        if row.traditional_name:
            province_data["traditional_names"].append(row.traditional_name.toPython())

    return province_data

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/search_by_province', methods=['GET'])
def search_by_province():
    province_name = request.args.get('province', '').strip()
    lang = request.args.get('lang', 'th')

    if not province_name:
        return jsonify({"message": "กรุณาป้อนชื่อจังหวัด" if lang == "th" else "Please enter a province name"}), 400

    result = get_province_data(province_name, lang)

    return app.response_class(
        response=json.dumps(result, ensure_ascii=False, indent=2),
        status=200,
        mimetype="application/json"
    )

@app.route('/img/<filename>')
def get_image(filename):
    return send_from_directory(app.config['IMG_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
