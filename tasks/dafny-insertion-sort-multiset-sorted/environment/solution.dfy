// SPEC-BEGIN
predicate Sorted(a: array<int>, lo: int, hi: int)
  reads a
  requires 0 <= lo <= hi <= a.Length
{
  forall i, j :: lo <= i < j < hi ==> a[i] <= a[j]
}

ghost function ArrayMultiset(a: array<int>): multiset<int>
  reads a
{
  multiset(a[..])
}

method InsertionSort(a: array<int>)
  modifies a
  ensures Sorted(a, 0, a.Length)
  ensures ArrayMultiset(a) == old(ArrayMultiset(a))
// SPEC-END
{
  // TODO: Add loop invariants, decreases, and helper lemmas to make this verify.
  var k := 1;
  while k < a.Length
  {
    var j := k;
    while j > 0 && a[j-1] > a[j]
    {
      a[j-1], a[j] := a[j], a[j-1];
      j := j - 1;
    }
    k := k + 1;
  }
}

method Main()
  decreases *
{
  var a1 := new int[6];
  a1[0], a1[1], a1[2], a1[3], a1[4], a1[5] := 3, 1, 4, 1, 5, 9;
  InsertionSort(a1);
  var i := 0;
  while i < a1.Length { print a1[i]; if i < a1.Length - 1 { print " "; } i := i + 1; }
  print "\n";
  var a2 := new int[4];
  a2[0], a2[1], a2[2], a2[3] := 5, 2, 8, 1;
  InsertionSort(a2);
  i := 0;
  while i < a2.Length { print a2[i]; if i < a2.Length - 1 { print " "; } i := i + 1; }
  print "\n";
}
