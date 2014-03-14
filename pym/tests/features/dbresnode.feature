Feature: Resource Tree
  Test creation and handling of resource nodes


  Scenario: create a new root node
      Given my root node is "root"/"unittest"
      When I create a new root node entry
      Then I should find new root node in restree table


  Scenario: create existing root node
      Given my root node "root"/"unittest" already exists
      When I create a new root node entry with this name and kind
      Then I get the existing one


  Scenario: create existing root node with different kind
      Given root node "root"/"unittest" already exists
      When I create a new root node with this name but different kind
      Then a ValueError exception is thrown