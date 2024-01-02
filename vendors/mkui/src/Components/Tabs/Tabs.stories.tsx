import { Tab } from "./Tabs"

function Article({ children }: { children?: React.ReactNode }) {
  return <article className="prose max-w-full">{children}</article>
}

function LoremIpsum() {
  return (
    <>
      <p>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur placerat diam quis pretium varius. Orci
        varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Nam at pellentesque metus.
        Morbi auctor sodales arcu, id gravida mauris ultrices et. Donec hendrerit, sapien nec volutpat luctus, nisi ex
        elementum neque, a ullamcorper mauris nulla sed sem. Nam mollis a ante id facilisis. Donec sodales eget erat
        eget pulvinar. In semper sodales odio, in commodo enim consequat ac. Suspendisse ullamcorper risus et nunc
        sagittis venenatis. Etiam ullamcorper lectus id ante tincidunt fringilla. Suspendisse ac mi et dolor tempus
        vehicula finibus in libero. Proin sagittis volutpat mi nec gravida. In hac habitasse platea dictumst. Etiam
        mattis est in nunc dictum, sed gravida metus vestibulum. Nam mattis egestas turpis, non sollicitudin nisl
        iaculis at. Sed ultricies eget magna sed sodales.
      </p>
      <p>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Ut sit amet aliquam nisl, vel pulvinar turpis. Donec
        justo mi, imperdiet at ultrices vulputate, placerat gravida tellus. Lorem ipsum dolor sit amet, consectetur
        adipiscing elit. Nunc vitae condimentum justo. Cras ac turpis a velit luctus maximus in sed purus. Proin
        faucibus mauris odio. Pellentesque euismod posuere aliquam. Sed lorem magna, tempor eget bibendum eget, pharetra
        quis metus.
      </p>
      <p>
        Donec quis bibendum erat, et dignissim purus. Sed ac venenatis nunc, ut malesuada libero. Sed convallis pulvinar
        ipsum, et ultricies orci malesuada id. Curabitur commodo pellentesque diam vitae placerat. Vivamus at ipsum
        urna. Sed pellentesque odio quis elit elementum pellentesque vitae nec felis. Suspendisse potenti. Ut pharetra
        nec nibh a viverra. Ut auctor nunc lacus, sed mattis tellus mollis nec. Maecenas gravida arcu ante, quis
        pharetra tortor sodales nec. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac
        turpis egestas. Vestibulum fringilla, augue quis fringilla euismod, nisi lorem tempor nunc, ut sollicitudin sem
        nisi ac justo. Proin interdum consectetur odio, id hendrerit nulla mattis at.
      </p>
      <p>
        Cras sit amet faucibus sapien. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos
        himenaeos. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Quisque ut
        rhoncus augue. Cras pulvinar diam vel erat congue imperdiet. Nulla quis risus et dolor tincidunt bibendum. Sed a
        arcu sit amet arcu convallis suscipit at in augue. Nam eget lorem a purus fermentum ornare vel eu arcu. Cras
        magna elit, imperdiet et pulvinar ut, tincidunt in nunc. Praesent egestas congue purus, id imperdiet dui
        pulvinar ac.
      </p>
      <p>
        Quisque augue felis, imperdiet ut purus a, mollis molestie ipsum. Donec scelerisque cursus commodo. Donec at
        tortor a velit aliquam tristique et eget quam. Interdum et malesuada fames ac ante ipsum primis in faucibus. Sed
        vel enim mi. Donec gravida, ex id tempor interdum, orci nisi pellentesque augue, vitae elementum urna elit
        accumsan sapien. Fusce eu lectus vitae velit lacinia blandit porttitor pretium ante. Orci varius natoque
        penatibus et magnis dis parturient montes, nascetur ridiculus mus. Aliquam mauris neque, hendrerit at blandit
        nec, ultrices nec augue. Donec in neque in purus lacinia dignissim. Curabitur suscipit metus lacus, vitae
        efficitur justo dictum at. Sed consequat vitae magna nec luctus. Curabitur placerat feugiat urna, a egestas ante
        maximus eu. Duis quis nulla ut ligula tempus tempus nec eget elit. Nunc convallis nunc velit, quis venenatis
        tortor ultricies ac. Sed at lorem nibh.
      </p>
    </>
  )
}

export const Default = () => (
  <Tab.Group>
    <Tab.List>
      <Tab>Foo</Tab>
      <Tab>Bar</Tab>
      <Tab>Baz</Tab>
      <Tab>Trombone shorty</Tab>
    </Tab.List>
    <Tab.Panels>
      <Tab.Panel>
        <Article>
          <p>This is the «foo» tab. Yeah.</p>
          <LoremIpsum />
        </Article>
      </Tab.Panel>
      <Tab.Panel>
        <Article>
          <p>This is the «bar» tab. Rock and roll.</p>
          <LoremIpsum />
        </Article>
      </Tab.Panel>
      <Tab.Panel>
        <Article>
          <p>This is the «baz» tab. Whatever.</p>
          <LoremIpsum />
        </Article>
      </Tab.Panel>
      <Tab.Panel>
        <Article>
          <p>And now for something completely different.</p>
          <p>This tab have very few content.</p>
        </Article>
      </Tab.Panel>
    </Tab.Panels>
  </Tab.Group>
)
