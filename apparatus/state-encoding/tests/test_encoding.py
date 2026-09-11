import unittest

from yurei_state_encoding import (FieldSpec, ObservationSchema, ObservationSnapshot,
                                  decode_compact, decode_json, encode_compact,
                                  encode_json, measure_encodings)


class EncodingTests(unittest.TestCase):
    def setUp(self):
        self.schema=ObservationSchema("room",1,(
            FieldSpec("bed","human at bed","boolean"),
            FieldSpec("desk","human at desk","boolean"),
            FieldSpec("motion","observed leg motion","number","normalized"),
        ))
        self.snapshot=ObservationSnapshot(self.schema,"2026-09-10T12:00:00Z","spectre",5,
                                          {"bed":False,"desk":True,"motion":0.25})

    def test_json_and_compact_round_trip(self):
        self.assertEqual(decode_json(encode_json(self.snapshot),self.schema),self.snapshot)
        self.assertEqual(decode_compact(encode_compact(self.snapshot),self.schema),self.snapshot)
        namespaced=encode_compact(self.snapshot,include_namespace=True)
        self.assertIn("[ns:room.v1]",namespaced)
        self.assertEqual(decode_compact(namespaced,self.schema),self.snapshot)

    def test_encoding_is_deterministic_and_compact_is_smaller(self):
        first=measure_encodings(self.snapshot)
        self.assertEqual(first,measure_encodings(self.snapshot))
        self.assertLess(first["compact"]["utf8_bytes"],first["json"]["utf8_bytes"])

    def test_schema_mismatch_and_nonfinite_values_fail_closed(self):
        other=ObservationSchema("other",1,self.schema.fields)
        with self.assertRaises(ValueError): decode_compact(encode_compact(self.snapshot),other)
        with self.assertRaises(ValueError):
            ObservationSnapshot(self.schema,"2026-09-10T12:00:00Z","spectre",5,
                                {"bed":False,"desk":True,"motion":float("nan")})
        with self.assertRaises(ValueError):
            decode_compact(encode_compact(self.snapshot)+"[desk:false]",self.schema)
        with self.assertRaises(ValueError):
            decode_json(encode_json(self.snapshot)[:-1]+',"extra":1}',self.schema)


if __name__ == "__main__": unittest.main()
