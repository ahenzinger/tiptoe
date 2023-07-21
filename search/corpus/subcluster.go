package corpus

// TODO: Change to uint
type Subcluster struct {
  index   uint64
  size    uint64
}

func NewSubcluster(i, s uint64) *Subcluster {
  sc := Subcluster{
    index: i,
    size: s,
  }
  return &sc
}

func (sc Subcluster) Size() uint64 {
  return sc.size
}

func (sc Subcluster) Index() uint64 {
  return sc.index
}

func (sc *Subcluster) SetIndex(i uint64) {
  sc.index = i
}

func (sc *Subcluster) SetSize(s uint64) {
  sc.size = s
}
