"""Logic 'Steinway Piano 2' 샘플러 (EXS 매핑 + consolidated CAF 직접 읽기)."""
import struct
import numpy as np

LOGIC = "/Library/Application Support/Logic"
EXS = f"{LOGIC}/Sampler Instruments/01 Acoustic Pianos/Steinway Piano 2.exs"
CAF = f"{LOGIC}/EXS Factory Samples/01 Acoustic Pianos/Steinway Piano_consolidated.caf"
SR = 44100


def _caf_frames(path):
    d = open(path, "rb")
    hdr = d.read(8)
    assert hdr[:4] == b"caff"
    pos = 8
    while True:
        d.seek(pos)
        h = d.read(12)
        typ, size = h[:4], struct.unpack(">q", h[4:])[0]
        if typ == b"data":
            off = pos + 12 + 4  # edit count
            n = (size - 4) // 4
            return np.memmap(path, dtype=">i2", mode="r", offset=off, shape=(n, 2))
        pos += 12 + size


def _parse_exs(path):
    d = open(path, "rb").read()
    i, zones, groups = 0, [], []
    while i + 84 <= len(d) and d[i + 16:i + 20] == b"TBOS":
        sig, size = struct.unpack_from("<II", d, i)
        name = d[i + 20:i + 84].split(b"\0")[0].decode("latin1")
        b = d[i + 84:i + 84 + size]
        typ = sig >> 24
        if typ == 0x41:
            _, root, fine, _, vol, _, klo, khi, _, _, _, _ = struct.unpack_from("<BBbbbbBBBBBB", b, 0)
            raw = struct.unpack_from("<" + "I" * (len(b) // 4), b, 0)
            zones.append(dict(root=root, fine=fine, vol=vol, klo=klo, khi=khi,
                              start=raw[3], end=raw[6], group=raw[22]))
        elif typ == 0x42:
            groups.append(dict(name=name, vol=struct.unpack_from("<b", b, 0)[0], vlo=b[5], vhi=b[6]))
        i += size + 84
    return zones, groups


class Piano:
    def __init__(self):
        self.pcm = _caf_frames(CAF)
        self.zones, self.groups = _parse_exs(EXS)

    def zone(self, key, vel):
        for z in self.zones:
            g = self.groups[z["group"]]
            if g["name"].startswith("p"):
                continue
            if z["klo"] <= key <= z["khi"] and g["vlo"] <= vel <= g["vhi"]:
                return z, g
        raise KeyError((key, vel))

    def note(self, key, vel, dur, release=0.9):
        z, g = self.zone(key, vel)
        seg = np.asarray(self.pcm[z["start"]:z["end"]], dtype=np.float32) / 32768.0
        ratio = 2 ** ((key - z["root"]) / 12 + z["fine"] / 1200)
        need = int((dur + release) * SR)
        src = np.arange(min(need, int(len(seg) / ratio) - 1)) * ratio
        out = np.stack([np.interp(src, np.arange(len(seg)), seg[:, c]) for c in (0, 1)], 1)
        env = np.ones(len(out), np.float32)
        r0 = int(dur * SR)
        if r0 < len(out):
            t = np.arange(len(out) - r0) / SR
            env[r0:] = np.exp(-t / (release / 4.5))
        gain = 10 ** ((z["vol"] + g["vol"]) / 20) * (0.55 + 0.45 * vel / 127)
        return (out * env[:, None] * gain).astype(np.float32)
