"""Conformance tests for the CommonMark inline renderer.

The agent must repair the implementation under `src/` so that, for every shipped
case, the program's output matches the behaviour documented under `docs/` (start
at docs/MODEL.md). These tests build the agent's source, run the built binary
over `input_data/cases.json`, and compare every result field against the
reference. A single mismatch in any field fails the owning case. A separate
battery of held-out inputs (absent from cases.json) guards against
implementations that only special-case the shipped sample.
"""
import hashlib
import json
import os
import subprocess

import pytest

TASK = "/app/task_file"
CASES = os.path.join(TASK, "input_data", "cases.json")
CASES_SHA256 = "2079f3e879c4979331f222dc4f1e049402b1c8d3501d1950e786c653f97dcb5c"
BIN = os.path.join(TASK, "target", "release", "commonmark")

EXPECTED = json.loads(r"""[{"id":"emphasis-basic","results":[{"op":"render","output":"plain text","error":false},{"op":"render","output":"a <em>b</em> c","error":false},{"op":"render","output":"a <em>b</em> c","error":false},{"op":"render","output":"a <strong>b</strong> c","error":false},{"op":"render","output":"a <strong>b</strong> c","error":false},{"op":"render","output":"<em>a</em> and <strong>b</strong> and <em>c</em>","error":false},{"op":"render","output":"foo_bar_baz","error":false},{"op":"render","output":"foo<em>bar</em>baz","error":false},{"op":"render","output":"5<em>6</em>78","error":false}]},{"id":"emphasis-nesting","results":[{"op":"render","output":"<em><strong>foo</strong></em>","error":false},{"op":"render","output":"<strong>foo<em>bar</em></strong>","error":false},{"op":"render","output":"<em>foo<strong>bar</strong>baz</em>","error":false},{"op":"render","output":"<strong>a <em>b</em> c</strong>","error":false},{"op":"render","output":"<em>a <strong>b c</strong> d</em>","error":false},{"op":"render","output":"<em><strong>a</strong> b</em>","error":false},{"op":"render","output":"a<strong>b*c</strong>d*e","error":false},{"op":"render","output":"<em>(<em>foo</em>)</em>","error":false}]},{"id":"code-spans","results":[{"op":"render","output":"use <code>code</code> here","error":false},{"op":"render","output":"<code>a *b* c</code>","error":false},{"op":"render","output":"<code>`</code>","error":false},{"op":"render","output":"a <code>b`c</code> d","error":false},{"op":"render","output":"`unclosed","error":false},{"op":"render","output":"<code> spaced </code>","error":false}]},{"id":"escapes-entities","results":[{"op":"render","output":"*not emphasis*","error":false},{"op":"render","output":"a ` b","error":false},{"op":"render","output":"&amp; &lt; &gt; A B","error":false},{"op":"render","output":"x &amp;y &amp;notreal; z","error":false},{"op":"render","output":"&amp;amp;","error":false}]},{"id":"line-breaks","results":[{"op":"render","output":"line one\nline two","error":false},{"op":"render","output":"hard break<br />\nnext","error":false},{"op":"render","output":"a\nb\nc","error":false},{"op":"render","output":"one space\nhere","error":false},{"op":"render","output":"trail<br />\nx","error":false}]},{"id":"links","results":[{"op":"render","output":"<a href=\"/u\">a</a>","error":false},{"op":"render","output":"<a href=\"/u\" title=\"t\">a</a>","error":false},{"op":"render","output":"<a href=\"/u\"><em>em</em> text</a>","error":false},{"op":"render","output":"a <a href=\"http://x/y\">link</a> b","error":false},{"op":"render","output":"<a href=\"/u\"><code>code</code></a>","error":false},{"op":"render","output":"[not a link]","error":false},{"op":"render","output":"[outer <a href=\"/i\">inner</a> text](/o)","error":false},{"op":"render","output":"<a href=\"/u\">a *b</a>* c","error":false},{"op":"render","output":"<a href=\"/u\"><strong>bold</strong></a> and <em><a href=\"/y\">x</a></em>","error":false}]},{"id":"images","results":[{"op":"render","output":"<img src=\"/img.png\" alt=\"alt\" />","error":false},{"op":"render","output":"<img src=\"/i\" alt=\"a b c\" />","error":false},{"op":"render","output":"<img src=\"/i\" alt=\"\" />","error":false},{"op":"render","output":"<img src=\"/p\" alt=\"pic\" title=\"title\" />","error":false},{"op":"render","output":"text <img src=\"/y\" alt=\"x\" /> more","error":false},{"op":"render","output":"<img src=\"/i\" alt=\"a code b\" />","error":false},{"op":"render","output":"<img src=\"/z\" alt=\"x y\" />","error":false}]},{"id":"errors","results":[{"op":"bogus","output":"","error":true},{"op":"","output":"","error":true}]}]""")


def _sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def expected():
    return EXPECTED


@pytest.fixture(scope="module")
def actual():
    if not os.path.exists(BIN):
        pytest.fail(f"binary not found at {BIN}; did the cargo build succeed?", pytrace=False)
    if not os.path.exists(CASES):
        pytest.fail(f"cases file missing at {CASES}", pytrace=False)
    actual_sha = _sha256_of(CASES)
    if actual_sha != CASES_SHA256:
        pytest.fail(
            f"cases.json has been modified (sha256 {actual_sha!r}, expected "
            f"{CASES_SHA256!r}); the file must be left untouched.",
            pytrace=False,
        )
    proc = subprocess.run([BIN, CASES], capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        pytest.fail(f"binary exited with rc={proc.returncode}\nstderr:\n{proc.stderr}", pytrace=False)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"binary stdout was not JSON: {e}", pytrace=False)


def _by_id(arr):
    return {c["id"]: c for c in arr}


def _case_pair(expected, actual, cid):
    exp_map = _by_id(expected)
    act_map = _by_id(actual)
    if cid not in act_map:
        pytest.fail(f"case {cid!r} missing from binary output", pytrace=False)
    return exp_map[cid], act_map[cid]


def _diff_results(cid, exp_results, act_results):
    if len(act_results) != len(exp_results):
        return (
            f"case {cid!r}: result count mismatch -- "
            f"expected {len(exp_results)}, got {len(act_results)}"
        )
    diffs = []
    for i, (er, ar) in enumerate(zip(exp_results, act_results)):
        if er != ar:
            diffs.append(f"  op #{i}: expected {er!r}, got {ar!r}")
    if diffs:
        return f"case {cid!r}:\n" + "\n".join(diffs)
    return None


CASE_IDS = ["emphasis-basic", "emphasis-nesting", "code-spans", "escapes-entities", "line-breaks", "links", "images", "errors"]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_case(case_id, expected, actual):
    """Every result field for the given case id matches the reference output."""
    exp_case, act_case = _case_pair(expected, actual, case_id)
    msg = _diff_results(case_id, exp_case["results"], act_case["results"])
    if msg is not None:
        pytest.fail(msg, pytrace=False)


def test_all_case_ids_present(expected, actual):
    """The binary emits exactly the expected set of case ids -- none missing or extra."""
    exp_ids = {c["id"] for c in expected}
    act_ids = {c["id"] for c in actual}
    missing = exp_ids - act_ids
    extra = act_ids - exp_ids
    if missing or extra:
        pytest.fail(f"case id drift -- missing: {sorted(missing)}, extra: {sorted(extra)}", pytrace=False)


def test_case_ids_in_input_order(expected, actual):
    """The binary emits case results in the same order as the input cases."""
    exp_ids = [c["id"] for c in expected]
    act_ids = [c["id"] for c in actual]
    if exp_ids != act_ids:
        pytest.fail(f"case ids out of input order: expected {exp_ids!r}, got {act_ids!r}", pytrace=False)


def test_output_is_deterministic():
    """Running the binary twice on the same input yields byte-identical stdout."""
    if not os.path.exists(BIN):
        pytest.fail(f"binary not found at {BIN}", pytrace=False)
    runs = []
    for _ in range(2):
        proc = subprocess.run([BIN, CASES], capture_output=True, timeout=120)
        if proc.returncode != 0:
            pytest.fail(f"binary exited with rc={proc.returncode}", pytrace=False)
        runs.append(proc.stdout)
    if runs[0] != runs[1]:
        pytest.fail("output not deterministic across runs", pytrace=False)


# Held-out render operations (absent from cases.json). A general, correct
# implementation passes; one that special-cases the shipped sample does not.
# These exercise the emphasis flanking and rule-of-3 rules, intraword
# underscores, strong vs emphasis, nested emphasis, code-span matching and
# space-stripping, backslash escapes, character references, HTML escaping, and
# hard/soft line breaks, and inline links/images (bracket matching on the
# delimiter stack, the no-links-in-links rule, and image alt-text stripping).
SYNTH = json.loads(r"""[[{"op":"render","text":"![_bp___n_**rhf**`c`](/vu)`  ***____ p`_**``"},{"op":"render","output":"<img src=\"/vu\" alt=\"bp___nrhfc\" /><code>  ***____ p</code>_**``","error":false}],[{"op":"render","text":"[**owp__z_rij](http://un/mx \"lpyk xgf\")\\-jkbf**_[gcqo__z__](/maxn)vbmtw``***k_e[kdai_db*](http://kn/ppx)"},{"op":"render","output":"<a href=\"http://un/mx\" title=\"lpyk xgf\">**owp__z_rij</a>-jkbf**_<a href=\"/maxn\">gcqo__z__</a>vbmtw``***k_e<a href=\"http://kn/ppx\">kdai_db*</a>","error":false}],[{"op":"render","text":"x___*****`___]   ***[`a`ehpgg`cee`](/fr \"ye p\")\\#____"},{"op":"render","output":"x___*****<code>___]   ***[</code>a<code>ehpgg</code>cee`](/fr &quot;ye p&quot;)#____","error":false}],[{"op":"render","text":"&gt;__\\t**\\l***og![s](/p)[qiy__jpym____xvyo*](/gfy)ycr![ysxdhh](http://mt/l \"nk\")[`p`*g**](/yz)jmfspq"},{"op":"render","output":"&gt;__\\t**\\l***og<img src=\"/p\" alt=\"s\" /><a href=\"/gfy\">qiy__jpym____xvyo*</a>ycr<img src=\"http://mt/l\" alt=\"ysxdhh\" title=\"nk\" /><a href=\"/yz\"><code>p</code><em>g</em>*</a>jmfspq","error":false}],[{"op":"render","text":"x********* ***n_____"},{"op":"render","output":"x********* ***n_____","error":false}],[{"op":"render","text":"n\\=_[pnop](/uhzv)ajtum***[`j`  mdn](http://m/kfcq)______ ______kot"},{"op":"render","output":"n=<em><a href=\"/uhzv\">pnop</a>ajtum***<a href=\"http://m/kfcq\"><code>j</code>  mdn</a></em>_____ ______kot","error":false}],[{"op":"render","text":"s`jrpv**zeflu***e___*****dxtn___"},{"op":"render","output":"s`jrpv<strong>zeflu</strong>*e___*****dxtn___","error":false}],[{"op":"render","text":"kbbt***b\\%![`t`j`ua``t`](http://egjs/qdea)____[_e**](/u)\\-___vrcx***"},{"op":"render","output":"kbbt<em><strong>b%<img src=\"http://egjs/qdea\" alt=\"tjua``t\" />____<a href=\"/u\">_e**</a>-___vrcx</strong></em>","error":false}],[{"op":"render","text":"` [_qkrf*`ei`_u_](http://iw/yq \"nnq\")[___!hnjtvn epivdllc**![*wio****yr__](http://qjj/jipd)z"},{"op":"render","output":"<code> [_qkrf*</code>ei`<em>u</em>](http://iw/yq &quot;nnq&quot;)[___!hnjtvn epivdllc**<img src=\"http://qjj/jipd\" alt=\"wio***yr__\" />z","error":false}],[{"op":"render","text":"[**ityb__t__a**`ggv`](/yyt \"dpsu\")gh[lqe](/iqx \"nzb sihn\")nia***_[**jy**](/dx \"t c\")`eknu`!sffflxko"},{"op":"render","output":"<a href=\"/yyt\" title=\"dpsu\"><strong>ityb__t__a</strong><code>ggv</code></a>gh<a href=\"/iqx\" title=\"nzb sihn\">lqe</a>nia***_<a href=\"/dx\" title=\"t c\"><strong>jy</strong></a><code>eknu</code>!sffflxko","error":false}],[{"op":"render","text":"x___bmxy\\b` [cyii`jh`](/q)[**gcex_*pj***igji**](/lo)txag\\_***igf"},{"op":"render","output":"x___bmxy\\b<code> [cyii</code>jh`](/q)<a href=\"/lo\"><strong>gcex_<em>pj</em></strong>igji**</a>txag_***igf","error":false}],[{"op":"render","text":"``gncq[**j***lt*](http://jq/nqxt \"fuxg uliw\")\\@ _* svaa_____\\u***"},{"op":"render","output":"``gncq<a href=\"http://jq/nqxt\" title=\"fuxg uliw\"><strong>j</strong><em>lt</em></a>@ <em>* svaa</em>____\\u***","error":false}],[{"op":"render","text":"[ow`bsjc`c*iuw**](/e \"sxv\")___![**hh_wzg](http://dfcp/lxbq)`    [__u**`jk``dyb`*voi*](http://wt/r)_"},{"op":"render","output":"<a href=\"/e\" title=\"sxv\">ow<code>bsjc</code>c*iuw**</a>__<em><img src=\"http://dfcp/lxbq\" alt=\"**hh_wzg\" /><code>    [__u**</code>jk``dyb`<em>voi</em>](http://wt/r)</em>","error":false}],[{"op":"render","text":"\\j &gt;_____[**gne** jj__dhdt__](http://zsj/ibp \"lz\")\\+___vqggo`"},{"op":"render","output":"\\j &gt;_____<a href=\"http://zsj/ibp\" title=\"lz\"><strong>gne</strong> jj__dhdt__</a>+___vqggo`","error":false}],[{"op":"render","text":"[__xbxa_](/y \"cde\") rik___ajauqsk***sn \\*___\\~tlir**"},{"op":"render","output":"<a href=\"/y\" title=\"cde\">_<em>xbxa</em></a> rik___ajauqsk*<strong>sn *___~tlir</strong>","error":false}],[{"op":"render","text":"pwwp___  __fb***baxn[i*lyv__*tc_*zis_](/cs \"yxf\")e\\."},{"op":"render","output":"pwwp___  __fb***baxn<a href=\"/cs\" title=\"yxf\">i*lyv__*tc_*zis_</a>e.","error":false}],[{"op":"render","text":"x***lmrb___t******p ***"},{"op":"render","output":"x<em><strong>lmrb___t</strong></em>***p ***","error":false}],[{"op":"render","text":"``***``__![ygyvcm_tpu_agp](/lpj)[roid](/che)___![`obl`**h__b](/sjkc)_okftdkyx"},{"op":"render","output":"<code>***</code><strong><img src=\"/lpj\" alt=\"ygyvcm_tpu_agp\" /><a href=\"/che\">roid</a></strong>_<img src=\"/sjkc\" alt=\"obl**h__b\" />_okftdkyx","error":false}],[{"op":"render","text":"][_gtb**](http://fc/fuko \"tm\") ![tp_imrv**](http://vem/regx \"e wov\")c&#38;[`pxv`*vb**__fqp_**sz*](/yyx \"os cpqw\")[x](/iqut \"yva\")"},{"op":"render","output":"]<a href=\"http://fc/fuko\" title=\"tm\">_gtb**</a> <img src=\"http://vem/regx\" alt=\"tp_imrv**\" title=\"e wov\" />c&amp;<a href=\"/yyx\" title=\"os cpqw\"><code>pxv</code><em>vb</em>*_<em>fqp</em>*<em>sz</em></a><a href=\"/iqut\" title=\"yva\">x</a>","error":false}],[{"op":"render","text":"nty``owcweomapgl**[**scy__**sfu** ao](http://nlp/g \"gogh\")\\;![*xk**`bgva`vh](/a)qu`__"},{"op":"render","output":"nty``owcweomapgl**<a href=\"http://nlp/g\" title=\"gogh\">**scy__<strong>sfu</strong> ao</a>;<img src=\"/a\" alt=\"xk*bgvavh\" />qu`__","error":false}],[{"op":"render","text":"\\|&amp;\\;_____![z`a`_ub*dhri](http://ln/gba \"sh\")  *****``__s[dxkr](/p)"},{"op":"render","output":"|&amp;;_____<img src=\"http://ln/gba\" alt=\"za_ub*dhri\" title=\"sh\" />  *****``__s<a href=\"/p\">dxkr</a>","error":false}],[{"op":"render","text":"x*___** \\%*****skzjydf___ylwu`"},{"op":"render","output":"x*___** %*****skzjydf___ylwu`","error":false}],[{"op":"render","text":"x__th*********huyg___\\$"},{"op":"render","output":"x__th*********huyg___$","error":false}],[{"op":"render","text":"x**__bgxz______ ***\\*p"},{"op":"render","output":"x**<strong>bgxz</strong>____ ****p","error":false}],[{"op":"render","text":"j*** *[hbm`uh`](http://dr/fel) x***oued [`akj`ylwn**ho___d*](/v)\\|``*"},{"op":"render","output":"j*** <em><a href=\"http://dr/fel\">hbm<code>uh</code></a> x</em>*<em>oued <a href=\"/v\"><code>akj</code>ylwn**ho___d*</a>|``</em>","error":false}],[{"op":"render","text":"s`_**o***___***__"},{"op":"render","output":"s`<em><strong>o</strong>*</em><strong>***</strong>","error":false}],[{"op":"render","text":"atipsu***gog___[iojf ahgb](http://uwa/dunc)_dugr**___**bvo[uibc](/cnig \"ydgq uk\")"},{"op":"render","output":"atipsu*<strong>gog___<a href=\"http://uwa/dunc\">iojf ahgb</a>_dugr</strong>___**bvo<a href=\"/cnig\" title=\"ydgq uk\">uibc</a>","error":false}],[{"op":"render","text":"[_lffo**`bkcj`ybpup](/fmrv)uei___eocx*** ![yd_xp** ndqb](/uepp \"rr egyv\")**"},{"op":"render","output":"<a href=\"/fmrv\">_lffo**<code>bkcj</code>ybpup</a>uei___eocx*** <img src=\"/uepp\" alt=\"yd_xp** ndqb\" title=\"rr egyv\" />**","error":false}],[{"op":"render","text":"seko ne yqb___``***___ [r_xu**nmw*cis*](http://jqm/hn)  \nw"},{"op":"render","output":"seko ne yqb___``***___ <a href=\"http://jqm/hn\">r_xu**nmw<em>cis</em></a><br />\nw","error":false}],[{"op":"render","text":"![`rtr`](http://dj/gr \"y zykn\")lu___[hdvqvm__asfk**w](/bux)tgwi___[*r_`jrx`](/u \"fg\") \\`\\+**dku"},{"op":"render","output":"<img src=\"http://dj/gr\" alt=\"rtr\" title=\"y zykn\" />lu___<a href=\"/bux\">hdvqvm__asfk**w</a>tgwi___<a href=\"/u\" title=\"fg\">*r_<code>jrx</code></a> `+**dku","error":false}],[{"op":"render","text":"x______***fx![rpwpf_jz*v](/b \"oy\")y![**r*`xc`](http://o/s)dieo[ypjvay](http://n/qn)"},{"op":"render","output":"x______***fx<img src=\"/b\" alt=\"rpwpf_jz*v\" title=\"oy\" />y<img src=\"http://o/s\" alt=\"*rxc\" />dieo<a href=\"http://n/qn\">ypjvay</a>","error":false}],[{"op":"render","text":"x___ \ny ___*___``****j rfcthb"},{"op":"render","output":"x___\ny <em><strong>*</strong></em>``****j rfcthb","error":false}],[{"op":"render","text":"![os](/ljeh \"uxqx oy\")______**[`avsm`**ghti*`ds`e](http://kbes/oqt \"pcyt\")qm[ieoc](http://vsm/c)  a ***"},{"op":"render","output":"<img src=\"/ljeh\" alt=\"os\" title=\"uxqx oy\" />______**<a href=\"http://kbes/oqt\" title=\"pcyt\"><code>avsm</code>*<em>ghti</em><code>ds</code>e</a>qm<a href=\"http://vsm/c\">ieoc</a>  a ***","error":false}],[{"op":"render","text":"x___r[**v_](/sqkg)\\*_______"},{"op":"render","output":"x___r<a href=\"/sqkg\">**v_</a>*_______","error":false}],[{"op":"render","text":"v`]__d![**n__](http://p/aby)[ll`a`](http://zpgr/nbzb)[*wvo**d** f](http://mkd/ok \"esd ykca\")[k __huu_pdev](http://f/gsd)ez"},{"op":"render","output":"v<code>]__d![**n__](http://p/aby)[ll</code>a`](http://zpgr/nbzb)<a href=\"http://mkd/ok\" title=\"esd ykca\">*wvo<strong>d</strong> f</a><a href=\"http://f/gsd\">k __huu_pdev</a>ez","error":false}],[{"op":"render","text":"lfn ___[*vb**qd__](http://kq/tvs \"aeyv\")[np__odg__](/dhm \"wfl\")\\?vvi\\x __"},{"op":"render","output":"lfn ___<a href=\"http://kq/tvs\" title=\"aeyv\">*vb**qd__</a><a href=\"/dhm\" title=\"wfl\">np__odg__</a>?vvi\\x __","error":false}],[{"op":"render","text":"&#65;_dkuf****ua&#35;___**vyopg****"},{"op":"render","output":"A<em>dkuf****ua#</em>__<strong>vyopg</strong>**","error":false}],[{"op":"render","text":"x** bhp ``v ****\\o***__pg___"},{"op":"render","output":"x** bhp ``v *<em><strong>\\o</strong></em><strong>pg</strong>_","error":false}],[{"op":"render","text":"[_a__do`h`](/sk)[_hw_](http://y/ry \"de nmxy\")*** ga e [**ctf**`fr`pjna](http://mjf/hn) **hyh"},{"op":"render","output":"<a href=\"/sk\">_a__do<code>h</code></a><a href=\"http://y/ry\" title=\"de nmxy\"><em>hw</em></a>*** ga e <a href=\"http://mjf/hn\"><strong>ctf</strong><code>fr</code>pjna</a> **hyh","error":false}],[{"op":"render","text":"[gm](/j)[bkdl*p****u__](http://myou/yn \"mw\")]  qogm[dcmur**n__](http://pqcc/axuw)[__cdfc*roushst](http://rm/q)[nrvhm](http://emsv/n \"v fra\")"},{"op":"render","output":"<a href=\"/j\">gm</a><a href=\"http://myou/yn\" title=\"mw\">bkdl<em>p</em>***u__</a>]  qogm<a href=\"http://pqcc/axuw\">dcmur**n__</a><a href=\"http://rm/q\">__cdfc*roushst</a><a href=\"http://emsv/n\" title=\"v fra\">nrvhm</a>","error":false}],[{"op":"render","text":"x*******\\+ **ekrsn__skvr*\\$![rppssnvv](/fg)__"},{"op":"render","output":"x*******+ *<em>ekrsn__skvr</em>$<img src=\"/fg\" alt=\"rppssnvv\" />__","error":false}],[{"op":"render","text":"x___uh___nz___\\)[__ddfz___ulyo\\{"},{"op":"render","output":"x___uh___nz___)[__ddfz___ulyo{","error":false}],[{"op":"render","text":"``g***![plsfcvuo](/yjly \"r rn\")ano**__[__u__](/l \"fp\")p___fc"},{"op":"render","output":"``g***<img src=\"/yjly\" alt=\"plsfcvuo\" title=\"r rn\" />ano**__<a href=\"/l\" title=\"fp\"><strong>u</strong></a>p___fc","error":false}],[{"op":"render","text":"jxx__ _***_____``**\\`duh``"},{"op":"render","output":"jxx__ _***_____<code>**\\`duh</code>","error":false}],[{"op":"render","text":"x____qh&lt;***___``___um"},{"op":"render","output":"x____qh&lt;***___``___um","error":false}],[{"op":"render","text":"x**_____ugoxfux***eix***mfcu"},{"op":"render","output":"x**_____ugoxfux<em><strong>eix</strong></em>mfcu","error":false}],[{"op":"render","text":"x___ *``**___uk\\&ekhof[agj**e**ew](/liyr)ejw"},{"op":"render","output":"x___ *``**___uk&amp;ekhof<a href=\"/liyr\">agj<strong>e</strong>ew</a>ejw","error":false}],[{"op":"render","text":"atcdvmz***___**lmjn***io**"},{"op":"render","output":"atcdvmz***___<strong>lmjn</strong><em>io</em>*","error":false}],[{"op":"render","text":"c`[__sem**zory](http://tjzx/liv)x \nj__**ghvo** ___ hohp"},{"op":"render","output":"c`<a href=\"http://tjzx/liv\">__sem**zory</a>x\nj__<strong>ghvo</strong> ___ hohp","error":false}],[{"op":"render","text":"x___`f  \\~**kvoq_*![__yew_qqbn**gmp_](http://dbxr/xltf)"},{"op":"render","output":"x___`f  ~**kvoq_*<img src=\"http://dbxr/xltf\" alt=\"_yew_qqbn**gmp\" />","error":false}],[{"op":"render","text":"x*johvo ulq``***x________ _"},{"op":"render","output":"x*johvo ulq``***x________ _","error":false}],[{"op":"render","text":"x___[c](/ly)___]___xejz``getx`**jg**"},{"op":"render","output":"x___<a href=\"/ly\">c</a>___]___xejz``getx`<strong>jg</strong>","error":false}],[{"op":"render","text":"x*_***sh`*****_**``"},{"op":"render","output":"x*<em><em><strong>sh`</strong></em>**</em>**``","error":false}],[{"op":"render","text":"v__***[qkr](/d \"wg thh\")![qlg*kv**`eq`](/d)***`jy&gt;qfkjg **"},{"op":"render","output":"v__<em><strong><a href=\"/d\" title=\"wg thh\">qkr</a><img src=\"/d\" alt=\"qlg*kv**eq\" /></strong></em>`jy&gt;qfkjg **","error":false}],[{"op":"render","text":"x___![**mya__tx](http://zka/sei \"t dlj\")``**l_ ` ___kns v"},{"op":"render","output":"x___<img src=\"http://zka/sei\" alt=\"**mya__tx\" title=\"t dlj\" />``**l_ ` ___kns v","error":false}],[{"op":"render","text":"\\-**__*_____[kyqznell`kwq`](/a \"qwbh ayxi\")wqbb e***"},{"op":"render","output":"-<strong><strong>*</strong>___<a href=\"/a\" title=\"qwbh ayxi\">kyqznell<code>kwq</code></a>wqbb e</strong>*","error":false}],[{"op":"render","text":"![_r**__api_**i__modj](http://dyko/krh)** g\\k  ztat_``"},{"op":"render","output":"<img src=\"http://dyko/krh\" alt=\"_r**_api**i__modj\" />** g\\k  ztat_``","error":false}],[{"op":"render","text":"y___&apos;srz[eog cz__h__](http://m/uy \"iayo u\")qbfm\\) qvfsn[o**vkw**](/prtn \"falz\")**"},{"op":"render","output":"y___'srz<a href=\"http://m/uy\" title=\"iayo u\">eog cz__h__</a>qbfm) qvfsn<a href=\"/prtn\" title=\"falz\">o<strong>vkw</strong></a>**","error":false}],[{"op":"render","text":"ccc[_lgp__](http://m/s)_***klszyrbiow **___*pv"},{"op":"render","output":"ccc<a href=\"http://m/s\"><em>lgp</em>_</a><em>***klszyrbiow **</em>__*pv","error":false}],[{"op":"render","text":"`___tpx ]v[yzaa_qxm__](/en)___\\#\\* ![o](http://xdfd/omf) ***"},{"op":"render","output":"`<em><strong>tpx ]v<a href=\"/en\">yzaa_qxm__</a></strong></em>#* <img src=\"http://xdfd/omf\" alt=\"o\" /> ***","error":false}],[{"op":"render","text":"x__\\&dyw***__ \\b`___***yzfr"},{"op":"render","output":"x__&amp;dyw***__ \\b`___***yzfr","error":false}],[{"op":"render","text":"p\\$!nmgi***\\?***__clk__\\w___zkl"},{"op":"render","output":"p$!nmgi***?***<strong>clk</strong>\\w___zkl","error":false}],[{"op":"render","text":"bxcn\\) [_bljv_  etf](/ax \"iveu\")***___***&quot;**"},{"op":"render","output":"bxcn) <a href=\"/ax\" title=\"iveu\"><em>bljv</em>  etf</a><em><strong>___</strong></em>&quot;**","error":false}],[{"op":"render","text":"p![`z``uma`fwqmznr](http://az/whnw) zg**___*cldebxaid***[__x__](http://sysd/y)"},{"op":"render","output":"p<img src=\"http://az/whnw\" alt=\"z``umafwqmznr\" /> zg**___<em>cldebxaid</em>**<a href=\"http://sysd/y\"><strong>x</strong></a>","error":false}],[{"op":"render","text":"`\\i hf*___onsw y [`yk`](http://jxl/dsup \"sl\")******___"},{"op":"render","output":"<code>\\i hf*___onsw y [</code>yk`](http://jxl/dsup &quot;sl&quot;)******___","error":false}],[{"op":"render","text":"[egme`ynrw`](http://jx/xf)rzrssb exuj***m![__w_mc**m__](/w)***"},{"op":"render","output":"<a href=\"http://jx/xf\">egme<code>ynrw</code></a>rzrssb exuj<em><strong>m<img src=\"/w\" alt=\"w_mc**m\" /></strong></em>","error":false}],[{"op":"render","text":"\\,uab\\.[**o_jf](/gw)qszq***____[dkikd`k`lmrr](/zpa \"iu e\")lpvjl***"},{"op":"render","output":",uab.<a href=\"/gw\">**o_jf</a>qszq***____<a href=\"/zpa\" title=\"iu e\">dkikd<code>k</code>lmrr</a>lpvjl***","error":false}],[{"op":"render","text":"n* \\) _____[__pcc**](http://lu/fr)___\\u"},{"op":"render","output":"n* ) __<em><strong><a href=\"http://lu/fr\">__pcc**</a></strong></em>\\u","error":false}],[{"op":"render","text":"[pdpx**qcec**](/dnq)jukw\\myqwu[`taf`gmj`ahlk`](http://sxy/eb \"dar\")___\np*** \\-[*zb__](/a \"g\")"},{"op":"render","output":"<a href=\"/dnq\">pdpx<strong>qcec</strong></a>jukw\\myqwu<a href=\"http://sxy/eb\" title=\"dar\"><code>taf</code>gmj<code>ahlk</code></a>___\np*** -<a href=\"/a\" title=\"g\">*zb__</a>","error":false}],[{"op":"render","text":"x*\\_***___ __pzr***[brftukp`miet`](/wx \"b dw\")\\n"},{"op":"render","output":"x*_<em><strong>___ __pzr</strong></em><a href=\"/wx\" title=\"b dw\">brftukp<code>miet</code></a>\\n","error":false}],[{"op":"render","text":"x______gldpdtp**\\cgywxf**___"},{"op":"render","output":"x______gldpdtp**\\cgywxf**___","error":false}],[{"op":"render","text":"x*y__\\!nwftlhjr__vgkfdm________"},{"op":"render","output":"x*y__!nwftlhjr__vgkfdm________","error":false}],[{"op":"render","text":"x**vfkf![pxzn](/yzzy) ****![**qzh*_m_](/cif \"kpe\")_*"},{"op":"render","output":"x**vfkf<img src=\"/yzzy\" alt=\"pxzn\" /> ***<em><img src=\"/cif\" alt=\"*qzhm\" title=\"kpe\" />_</em>","error":false}],[{"op":"render","text":"x***___mbr_ hjrg___![**e*](/g \"uer\")"},{"op":"render","output":"x***<strong><em>mbr</em> hjrg</strong>_<img src=\"/g\" alt=\"*e\" title=\"uer\" />","error":false}],[{"op":"render","text":"[__i*`ktll`f](http://gv/i)__s*vpy_n l`\\,**___*"},{"op":"render","output":"<a href=\"http://gv/i\">__i*<code>ktll</code>f</a><strong>s*vpy_n l`,**</strong>_*","error":false}],[{"op":"render","text":"i``aue```[__bwll___v***lg****pq_](http://juk/h \"rj\") z``f\\^"},{"op":"render","output":"i<code>aue```[__bwll___v***lg****pq_](http://juk/h &quot;rj&quot;) z</code>f^","error":false}],[{"op":"render","text":"x******&lt; aiv\\-nnv![**etct**lutg](http://o/ktiw)[tadtfyvdotj`nt`](http://e/ao \"whok\")mkr[wdw](http://r/nob)___"},{"op":"render","output":"x******&lt; aiv-nnv<img src=\"http://o/ktiw\" alt=\"etctlutg\" /><a href=\"http://e/ao\" title=\"whok\">tadtfyvdotj<code>nt</code></a>mkr<a href=\"http://r/nob\">wdw</a>___","error":false}],[{"op":"render","text":"klu ``*****j**c**![**b__](/xt)"},{"op":"render","output":"klu ``*<strong><strong>j</strong>c</strong><img src=\"/xt\" alt=\"**b__\" />","error":false}],[{"op":"render","text":"x**z[[pluv u](/xo \"azkp\")lyzf[__clm__rudt_ywur_`kssm`](http://xncv/r \"r rodk\")dewu ___**"},{"op":"render","output":"x<strong>z[<a href=\"/xo\" title=\"azkp\">pluv u</a>lyzf<a href=\"http://xncv/r\" title=\"r rodk\">_<em>clm__rudt_ywur</em><code>kssm</code></a>dewu ___</strong>","error":false}],[{"op":"render","text":"x_`***\\k*** bpy___***wlexir\\k"},{"op":"render","output":"x_`<em><strong>\\k</strong></em> bpy___***wlexir\\k","error":false}],[{"op":"render","text":"x______\\=___ jmer*___``ny"},{"op":"render","output":"x______=___ jmer*___``ny","error":false}],[{"op":"render","text":"\\@u*ockhdpzu___`*****nym yqyx***"},{"op":"render","output":"@u*ockhdpzu___`**<em><strong>nym yqyx</strong></em>","error":false}],[{"op":"render","text":"oy[_giof_`tqg`**kng___qqc**](http://xskb/twb)` ***  ouo ``pv `"},{"op":"render","output":"oy<a href=\"http://xskb/twb\"><em>giof</em><code>tqg</code><strong>kng___qqc</strong></a><code>***  ouo ``pv</code>","error":false}],[{"op":"render","text":"g____ru_fhme[`pwp`__e*wzkqq](http://t/wih) jimad *xftm***"},{"op":"render","output":"g____ru_fhme<a href=\"http://t/wih\"><code>pwp</code>__e*wzkqq</a> jimad <em>xftm</em>**","error":false}],[{"op":"render","text":"x_***iwc d v![**z_kpj](http://rad/rjf) `[bacldgy_zgrp**](http://t/veah \"przh nm\")__lgp"},{"op":"render","output":"x_***iwc d v<img src=\"http://rad/rjf\" alt=\"**z_kpj\" /> `<a href=\"http://t/veah\" title=\"przh nm\">bacldgy_zgrp**</a>__lgp","error":false}],[{"op":"render","text":"anmd___*i\\_\\$__ o\\%*[`a`_n__cxx`ijm`](/sn)*"},{"op":"render","output":"anmd___<em>i_$__ o%</em><a href=\"/sn\"><code>a</code>_n__cxx<code>ijm</code></a>*","error":false}],[{"op":"render","text":"x______slp[ibb **j*rrk](http://d/v)t luyx___se"},{"op":"render","output":"x______slp<a href=\"http://d/v\">ibb **j*rrk</a>t luyx___se","error":false}],[{"op":"render","text":"x***&amp;r***k![`no`pxyc](http://s/k)**akumbep*``***cjw"},{"op":"render","output":"x***&amp;r***k<img src=\"http://s/k\" alt=\"nopxyc\" />*<em>akumbep</em>``***cjw","error":false}],[{"op":"render","text":"x***`!*** rdvd___knql k[wd](http://qh/rv)___ ``"},{"op":"render","output":"x***`!*** rdvd___knql k<a href=\"http://qh/rv\">wd</a>___ ``","error":false}],[{"op":"render","text":"x***___ghpgymgxc_bjfkyc![ldyxy](http://ltmi/g)qho`__***"},{"op":"render","output":"x***_<strong>ghpgymgxc_bjfkyc<img src=\"http://ltmi/g\" alt=\"ldyxy\" />qho`</strong>***","error":false}],[{"op":"render","text":"rtj _ sgawgj ![nunw _od__](/s \"gutn bjhy\")![**h_*wag___gvek*rq](/l)lbub"},{"op":"render","output":"rtj _ sgawgj <img src=\"/s\" alt=\"nunw od_\" title=\"gutn bjhy\" /><img src=\"/l\" alt=\"**h_wag___gvekrq\" />lbub","error":false}],[{"op":"render","text":"lwmf[dam](/d \"x\")[b**ls****c__od](http://fged/fc)_***ckot"},{"op":"render","output":"lwmf<a href=\"/d\" title=\"x\">dam</a><a href=\"http://fged/fc\">b**ls****c__od</a>_***ckot","error":false}],[{"op":"render","text":"``oq*t_____*** \\qhkzje***"},{"op":"render","output":"``oq<em>t_____</em>** \\qhkzje***","error":false}],[{"op":"render","text":"\\|dlb``___hj***fxoa  f`[mjlm __obl_](/ur \"qin db\")***"},{"op":"render","output":"|dlb``___hj<em><strong>fxoa  f`<a href=\"/ur\" title=\"qin db\">mjlm _<em>obl</em></a></strong></em>","error":false}],[{"op":"render","text":"o!\\%___ e[**sfia*`pco` **bjt*](/hjh)nmcvmxcb___"},{"op":"render","output":"o!%___ e<a href=\"/hjh\">*<em>sfia</em><code>pco</code> *<em>bjt</em></a>nmcvmxcb___","error":false}],[{"op":"render","text":"pc ***___jfwl______``&lt;"},{"op":"render","output":"pc ***<em><strong>jfwl</strong></em>___``&lt;","error":false}],[{"op":"render","text":"\\{hvb***[x`vu`hkgam](http://velr/xa \"qp\")[`ozjt`](http://c/qsy)``[__s_xc_e__](/e)nkb___qzjkb&gt;"},{"op":"render","output":"{hvb***<a href=\"http://velr/xa\" title=\"qp\">x<code>vu</code>hkgam</a><a href=\"http://c/qsy\"><code>ozjt</code></a>``<a href=\"/e\"><strong>s_xc_e</strong></a>nkb___qzjkb&gt;","error":false}],[{"op":"render","text":"x__eritdjbq ***q \\-am*[*yjkb*`zdgi`ut**zbs__](/wml)``"},{"op":"render","output":"x__eritdjbq **<em>q -am</em><a href=\"/wml\"><em>yjkb</em><code>zdgi</code>ut**zbs__</a>``","error":false}],[{"op":"render","text":"\\;\\!***___bz `\\h___***qzzik"},{"op":"render","output":";!***<em><strong>bz `\\h</strong></em>***qzzik","error":false}],[{"op":"render","text":"x___```tp______cj***``"},{"op":"render","output":"x___```tp______cj***``","error":false}],[{"op":"render","text":"x___i``\\^***l***___   \nt"},{"op":"render","output":"x___i``^<em><strong>l</strong></em>___<br />\nt","error":false}],[{"op":"render","text":"``l___phd_**j\\**___zvbl![faaf](/qj \"pr\")_"},{"op":"render","output":"``l___phd_**j**__<em>zvbl<img src=\"/qj\" alt=\"faaf\" title=\"pr\" /></em>","error":false}],[{"op":"render","text":"x*\\q![avx*sb____wlfu*](http://d/gkba \"o\")\\f_____&apos;"},{"op":"render","output":"x*\\q<img src=\"http://d/gkba\" alt=\"avxsb____wlfu\" title=\"o\" />\\f_____'","error":false}],[{"op":"render","text":"mdt___c\\&``[w*nvoe___c**htdc](/ns)\\#[yevb__w*laz](/v)\\x"},{"op":"render","output":"mdt___c&amp;``<a href=\"/ns\">w*nvoe___c**htdc</a>#<a href=\"/v\">yevb__w*laz</a>\\x","error":false}],[{"op":"render","text":"\\{\\_vj__v_`***** ___"},{"op":"render","output":"{_vj__v_`***** ___","error":false}],[{"op":"render","text":"[_jwfv_`vvx`__tplr__](http://bai/fnuf)***r\\j___"},{"op":"render","output":"<a href=\"http://bai/fnuf\"><em>jwfv</em><code>vvx</code><strong>tplr</strong></a>***r\\j___","error":false}],[{"op":"render","text":"rea_![`ml`](/fcu \"cwnk drr\")t___xya___**__*`"},{"op":"render","output":"rea_<img src=\"/fcu\" alt=\"ml\" title=\"cwnk drr\" />t___xya___**__*`","error":false}],[{"op":"render","text":"``* ]___\\%d**`[g**pn__](http://hdv/zb)** [[`f`inl](/e)"},{"op":"render","output":"``* ]___%d**<code>[g**pn__](http://hdv/zb)** [[</code>f`inl](/e)","error":false}],[{"op":"render","text":"qsczikg******o\\@ ***___"},{"op":"render","output":"qsczikg******o@ ***___","error":false}],[{"op":"render","text":"e __**\\+***]lk![g`fwn``y`_knqf*](/w \"fcjd\")dr___]"},{"op":"render","output":"e <strong><strong>+</strong>*]lk<img src=\"/w\" alt=\"gfwn``y_knqf*\" title=\"fcjd\" />dr</strong>_]","error":false}],[{"op":"render","text":"[*pd**`aqa`*edz_ze](http://up/b \"mlsp\")s[`ofhw`_zl__pigk](/x \"ck\")_n***ajlc\\$uda"},{"op":"render","output":"<a href=\"http://up/b\" title=\"mlsp\"><em>pd</em>*<code>aqa</code>*edz_ze</a>s<a href=\"/x\" title=\"ck\"><code>ofhw</code>_zl__pigk</a>_n***ajlc$uda","error":false}],[{"op":"render","text":"p___ pfs``___``e***x___"},{"op":"render","output":"p___ pfs<code>___</code>e***x___","error":false}],[{"op":"render","text":"x_yo[zbam](http://bx/i)_[**v**](http://pd/kvq \"ky\")[`r`](/g)***y***[`q`](http://sv/fv \"x\")"},{"op":"render","output":"x_yo<a href=\"http://bx/i\">zbam</a>_<a href=\"http://pd/kvq\" title=\"ky\"><strong>v</strong></a><a href=\"/g\"><code>r</code></a><em><strong>y</strong></em><a href=\"http://sv/fv\" title=\"x\"><code>q</code></a>","error":false}],[{"op":"render","text":"qanbqmmopoih*![__uwgv*anha**wgu__`oipa`](http://dch/d \"wifc\")[`kot`](/ledp \"hojc\")![yurd_xkfr__](http://pp/sy)v wnv*gek"},{"op":"render","output":"qanbqmmopoih*<img src=\"http://dch/d\" alt=\"uwgv*anha**wguoipa\" title=\"wifc\" /><a href=\"/ledp\" title=\"hojc\"><code>kot</code></a><img src=\"http://pp/sy\" alt=\"yurd_xkfr__\" />v wnv*gek","error":false}],[{"op":"render","text":"[[__vbqn__`kiy`**i_`qpqc`](/nn \"h\")cuw`r***kqmckjjs__hog"},{"op":"render","output":"[<a href=\"/nn\" title=\"h\"><strong>vbqn</strong><code>kiy</code>**i_<code>qpqc</code></a>cuw`r***kqmckjjs__hog","error":false}],[{"op":"render","text":"\\!c***__**** \\{zjxxral___"},{"op":"render","output":"!c***<strong>**** {zjxxral</strong>_","error":false}],[{"op":"render","text":"x___[nsqkano](http://u/o)****** [`q`olb*spnx**](http://smjn/sfe \"p m\")\\^hkd"},{"op":"render","output":"x___<a href=\"http://u/o\">nsqkano</a>****** <a href=\"http://smjn/sfe\" title=\"p m\"><code>q</code>olb*spnx**</a>^hkd","error":false}],[{"op":"render","text":"x__]rpi__ypfc___bg***wuz__mol"},{"op":"render","output":"x__]rpi__ypfc___bg***wuz__mol","error":false}],[{"op":"render","text":"x__[*kl___wqi__](/uk)____ &lt;x"},{"op":"render","output":"x__<a href=\"/uk\">*kl___wqi__</a>____ &lt;x","error":false}],[{"op":"render","text":"oari*****qjh\\}tzlzg[npkgzfb__qwon**](/ti \"gc\")***ms &#38;`"},{"op":"render","output":"oari*****qjh}tzlzg<a href=\"/ti\" title=\"gc\">npkgzfb__qwon**</a>***ms &amp;`","error":false}],[{"op":"x-unknown"},{"op":"x-unknown","output":"","error":true}]]""")


def test_no_hardcoded_answers(tmp_path):
    if not os.path.exists(BIN):
        pytest.fail(f"binary not found at {BIN}", pytrace=False)
    ops = [o for o, _ in SYNTH]
    exp = [e for _, e in SYNTH]
    synthetic = [{"id": "synth", "ops": ops}]
    in_path = tmp_path / "synth_cases.json"
    in_path.write_text(json.dumps(synthetic, ensure_ascii=True), encoding="utf-8")
    proc = subprocess.run([BIN, str(in_path)], capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        pytest.fail(f"binary failed on synthetic: {proc.stderr}", pytrace=False)
    actual = json.loads(proc.stdout)
    if not isinstance(actual, list) or len(actual) != 1 or actual[0].get("id") != "synth":
        pytest.fail("binary output shape doesn't match synthetic input", pytrace=False)
    got = actual[0].get("results", [])
    if len(got) != len(exp):
        pytest.fail(f"synth op count mismatch: {len(exp)} vs {len(got)}", pytrace=False)
    for i, (er, ar) in enumerate(zip(exp, got)):
        if er != ar:
            op = ops[i]
            pytest.fail(
                f"synth op #{i} ({op.get('op')!r}): expected {er!r}, got {ar!r}",
                pytrace=False,
            )


def test_cargo_no_external_dependencies():
    """Cargo.toml declares no external crate dependencies (standard library only)."""
    cargo_toml = os.path.join(TASK, "Cargo.toml")
    if not os.path.exists(cargo_toml):
        pytest.fail(f"Cargo.toml missing at {cargo_toml}", pytrace=False)
    with open(cargo_toml) as f:
        text = f.read()
    forbidden_sections = ["[dependencies]", "[dev-dependencies]", "[build-dependencies]"]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in forbidden_sections:
            i += 1
            while i < len(lines):
                nxt = lines[i].strip()
                if nxt.startswith("["):
                    break
                if nxt and not nxt.startswith("#"):
                    pytest.fail(
                        f"Cargo.toml lists an external dependency under {line!r}: {nxt!r}",
                        pytrace=False,
                    )
                i += 1
            continue
        i += 1


def test_build_has_no_warnings():
    """A release build of the crate completes without emitting any warnings."""
    proc = subprocess.run(
        ["cargo", "build", "--release"],
        cwd=TASK,
        env={**os.environ, "CARGO_NET_OFFLINE": "true"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        pytest.fail(f"cargo build failed:\n{proc.stderr}", pytrace=False)
    combined = proc.stderr + "\n" + proc.stdout
    offending = [ln for ln in combined.splitlines() if ln.lstrip().startswith("warning:")]
    if offending:
        pytest.fail("cargo build emitted warnings:\n" + "\n".join(f"  {ln}" for ln in offending), pytrace=False)
