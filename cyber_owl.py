import rdflib
from py2neo import Graph, Node, Relationship

# Replace the placeholders with your own Neo4j credentials.
neo4j_graph = Graph("bolt://localhost:7687", auth=("neo4j_username", "neo4j_password"))

# Load the OWL ontology file.
g = rdflib.Graph()
g.parse("path/to/your/ontology.owl")

# Prefixes for commonly used RDF, RDFS, and OWL terms.
RDF = rdflib.RDF
RDFS = rdflib.RDFS
OWL = rdflib.OWL

# Create a dictionary to store nodes (URIRefs as keys, Node objects as values).
nodes = {}

# Process classes, individuals, and their properties (labels and comments).
for entity_type in (OWL.Class, OWL.NamedIndividual):
    for entity in g.subjects(RDF.type, entity_type):
        labels = list(g.objects(entity, RDFS.label))
        label = labels[0] if labels else entity.split("#")[-1]

        comments = list(g.objects(entity, RDFS.comment))
        comment = comments[0] if comments else ""

        node = Node(label, uri=str(entity), comment=str(comment))
        nodes[entity] = node
        neo4j_graph.create(node)

# Process relationships (object properties and data properties).
for property_type in (OWL.ObjectProperty, OWL.DatatypeProperty):
    for prop in g.subjects(RDF.type, property_type):
        labels = list(g.objects(prop, RDFS.label))
        label = labels[0] if labels else prop.split("#")[-1]

        comments = list(g.objects(prop, RDFS.comment))
        comment = comments[0] if comments else ""

        for subject, object in g.subject_objects(prop):
            if subject in nodes and object in nodes:
                rel = Relationship(nodes[subject], label, nodes[object], uri=str(prop), comment=str(comment))
                neo4j_graph.create(rel)

# Process subclass axioms.
for subclass, superclass in g.subject_objects(RDFS.subClassOf):
    if subclass in nodes and superclass in nodes:
        sub_rel = Relationship(nodes[subclass], "SUBCLASS_OF", nodes[superclass])
        neo4j_graph.create(sub_rel)

# Process equivalence axioms.
for eq_class1, eq_class2 in g.subject_objects(OWL.equivalentClass):
    if eq_class1 in nodes and eq_class2 in nodes:
        eq_rel = Relationship(nodes[eq_class1], "EQUIVALENT_TO", nodes[eq_class2])
        neo4j_graph.create(eq_rel)

# Process annotation axioms.
for subject, annotation in g.subject_objects(OWL.annotatedSource):
    predicate = g.value(subject, OWL.annotatedProperty)
    obj = g.value(subject, OWL.annotatedTarget)
    if predicate and obj and subject in nodes:
        rel_label = predicate.split("#")[-1]
        rel = Relationship(nodes[subject], rel_label, obj)
        neo4j_graph.create(rel)

# Process individual axioms (class assertions).
for ind, cls in g.subject_objects(RDF.type):
    if ind in nodes and cls in nodes and cls != OWL.NamedIndividual:
        rel = Relationship(nodes[ind], "INSTANCE_OF", nodes[cls])
        neo4j_graph.create(rel)

# Process restrictions.
for cls, restriction in g.subject_objects(OWL.intersectionOf):
    if cls in nodes:
        for prop, value in g.predicate_objects(restriction):
            if prop == OWL.someValuesFrom or prop == OWL.allValuesFrom:
                if value in nodes:
                    rel_label = "RESTRICTION_ON" if prop == OWL.someValuesFrom else "ONLY_RESTRICTION_ON"
                    on_property = g.value(restriction, OWL.onProperty)
                    rel = Relationship(nodes[cls], rel_label, nodes[value], on_property=str(on_property))
                    neo4j_graph.create(rel)

# Process disjointness axioms.
for disj1, disj2 in g.subject_objects(OWL.disjointWith):
    if disj1 in nodes and disj2 in nodes:
        disj_rel = Relationship(nodes[disj1], "DISJOINT_WITH", nodes[disj2])
        neo4j_graph.create(disj_rel)

# Process inverse property axioms.
for prop1, prop2 in g.subject_objects(OWL.inverseOf):
    if prop1 in nodes and prop2 in nodes:
        inv_rel = Relationship(nodes[prop1], "INVERSE_OF", nodes[prop2])
        neo4j_graph.create(inv_rel)

# Process transitive property axioms.
for trans_prop in g.subjects(RDF.type, OWL.TransitiveProperty):
    if trans_prop in nodes:
        trans_rel = Relationship(nodes[trans_prop], "IS_TRANSITIVE", nodes[trans_prop])
        neo4j_graph.create(trans_rel)

print("Ontology successfully imported to Neo4j, including various axioms.")
